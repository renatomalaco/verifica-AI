"""Sign-in for the research area (R5a): invites, login, rotating refresh, logout and blocking."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable
from uuid import UUID, uuid4

from contracts import ResearchAccount, ResearchRoleInfo, ResearchUser
from scan_orchestrator.application.research_roles import UnknownRoleError
from scan_orchestrator.domain.research_access import (
    Account,
    LoginThrottle,
    RefreshSession,
    Role,
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


class CannotDisableSelfError(Exception):
    """Blocking yourself would leave the research area with no one to send invites."""


@dataclass(frozen=True)
class SignedIn:
    access_token: str
    refresh_token: str
    account: Account
    user: ResearchUser


def role_info(role: Role) -> ResearchRoleInfo:
    return ResearchRoleInfo(id=role.id, name=role.name, permissions=role.sorted_permissions())


def _user(account: Account, role: Role) -> ResearchUser:
    return ResearchUser(email=account.email, role=role_info(role), expires_at=account.expires_at)


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

    async def invite(self, email: str, role: str, expires_at: datetime | None = None) -> str:
        """Creates (or renews) the account and returns the one-time secret for the invite link."""
        if await self._repo.get_role(role) is None:
            raise UnknownRoleError(role)
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
        if (
            account is None
            or account.invite_expires_at is None
            or self._clock() >= account.invite_expires_at
        ):
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

    async def disable_for(self, actor_id: UUID, email: str) -> bool:
        """Blocking from the admin screen: the same as disable, except on yourself."""
        account = await self._repo.find_by_email(normalize_email(email))
        if account is not None and account.id == actor_id:
            raise CannotDisableSelfError()
        return await self.disable(email)

    async def list_accounts(self) -> list[ResearchAccount]:
        now = self._clock()
        roles = {role.id: role for role in await self._repo.list_roles()}
        accounts = sorted(await self._repo.list_accounts(), key=lambda account: account.email)
        return [
            ResearchAccount(
                **_user(a, roles[a.role]).model_dump(), status=a.status(now)
            )
            for a in accounts
        ]

    async def describe(self, account: Account) -> ResearchUser:
        return _user(account, await self._role_of(account))

    async def _role_of(self, account: Account) -> Role:
        # The foreign key in Postgres guarantees every account points at an existing role.
        return await self._repo.get_role(account.role)

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
        role = await self._role_of(account)
        return SignedIn(
            access_token=self._issuer.issue(account.id, role),
            refresh_token=raw,
            account=account,
            user=_user(account, role),
        )
