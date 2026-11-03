"""Sign-in for the research area (R5a): invites, login, rotating refresh, logout and blocking."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable
from uuid import UUID, uuid4

from contracts import ResearchRole
from scan_orchestrator.domain.research_access import (
    Account,
    LoginThrottle,
    RefreshSession,
    SessionState,
    hash_secret,
    new_secret,
    normalize_email,
    validate_password,
)
from scan_orchestrator.infrastructure.access_tokens import AccessTokenIssuer
from scan_orchestrator.infrastructure.passwords import PasswordHasher
from scan_orchestrator.infrastructure.research_account_repository import ResearchAccountRepository

REFRESH_TTL = timedelta(days=7)
INVITE_TTL = timedelta(hours=48)


class InvalidCredentialsError(Exception):
    """Deliberately generic: it never says whether the e-mail exists."""


class InviteInvalidError(Exception):
    pass


class SessionRejectedError(Exception):
    pass


@dataclass(frozen=True)
class SignedIn:
    access_token: str
    refresh_token: str
    account: Account


class ResearchAuth:
    def __init__(
        self,
        repository: ResearchAccountRepository,
        hasher: PasswordHasher,
        issuer: AccessTokenIssuer,
        throttle: LoginThrottle,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._repo = repository
        self._hasher = hasher
        self._issuer = issuer
        self._throttle = throttle
        self._clock = clock

    async def invite(self, email: str, role: ResearchRole, expires_at: datetime | None = None) -> str:
        """Creates (or renews) the account and returns the one-time secret for the invite link."""
        raw = new_secret()
        await self._repo.save_invite(
            email=normalize_email(email),
            role=role,
            expires_at=expires_at,
            invite_hash=hash_secret(raw),
            invite_expires_at=self._clock() + INVITE_TTL,
        )
        return raw

    async def accept_invite(self, raw_invite: str, password: str) -> None:
        account = await self._repo.find_by_invite(hash_secret(raw_invite))
        if account is None or account.invite_expires_at is None or self._clock() >= account.invite_expires_at:
            raise InviteInvalidError()
        validate_password(password)
        await self._repo.set_password(account.id, self._hasher.hash(password))

    async def login(self, email: str, password: str, ip: str) -> SignedIn:
        email = normalize_email(email)
        await self._throttle.register_attempt(email, ip)
        account = await self._repo.find_by_email(email)
        password_ok = self._hasher.verify(password, account.password_hash if account else None)
        if account is None or not password_ok or not account.can_sign_in(self._clock()):
            raise InvalidCredentialsError()
        return await self._start_session(account, family_id=uuid4())

    async def refresh(self, raw_refresh: str) -> SignedIn:
        now = self._clock()
        session = await self._repo.find_session(hash_secret(raw_refresh)) if raw_refresh else None
        if session is None:
            raise SessionRejectedError()
        state = session.state(now)
        if state is SessionState.EXPIRED:
            raise SessionRejectedError()
        if state is SessionState.REUSED or not await self._repo.mark_used(session.id, now):
            # An old token came back: someone holds a copy. End every token of this sign-in.
            await self._repo.revoke_family(session.family_id, now)
            raise SessionRejectedError()
        account = await self.current_account(session.account_id)
        if account is None:
            raise SessionRejectedError()
        return await self._start_session(account, family_id=session.family_id)

    async def logout(self, raw_refresh: str) -> None:
        session = await self._repo.find_session(hash_secret(raw_refresh)) if raw_refresh else None
        if session is not None:
            await self._repo.revoke_family(session.family_id, self._clock())

    async def disable(self, email: str) -> bool:
        """Blocks the account at once: no new sign-in, and its refresh tokens stop working."""
        account = await self._repo.find_by_email(normalize_email(email))
        if account is None:
            return False
        now = self._clock()
        await self._repo.disable(account.id, now)
        await self._repo.revoke_account_sessions(account.id, now)
        return True

    async def current_account(self, account_id: UUID) -> Account | None:
        account = await self._repo.get_account(account_id)
        return account if account and account.can_sign_in(self._clock()) else None

    async def _start_session(self, account: Account, family_id: UUID) -> SignedIn:
        raw = new_secret()
        await self._repo.add_session(
            RefreshSession(
                id=uuid4(),
                account_id=account.id,
                family_id=family_id,
                token_hash=hash_secret(raw),
                expires_at=self._clock() + REFRESH_TTL,
            )
        )
        return SignedIn(access_token=self._issuer.issue(account.id, account.role), refresh_token=raw, account=account)
