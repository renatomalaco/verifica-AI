"""Rules for the research area accounts (R5a). End users never sign in; only researchers do."""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID

from contracts import ResearchRole
from scan_orchestrator.domain.quota import QuotaStore

MIN_PASSWORD_LENGTH = 12


class WeakPasswordError(ValueError):
    pass


class TooManyAttemptsError(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__(f"Too many sign-in attempts; retry in {retry_after_seconds}s")
        self.retry_after_seconds = retry_after_seconds


@dataclass(frozen=True)
class Account:
    id: UUID
    email: str
    role: ResearchRole
    password_hash: str | None  # None until the invite is accepted
    expires_at: datetime | None = None
    disabled_at: datetime | None = None
    invite_hash: str | None = None
    invite_expires_at: datetime | None = None

    def can_sign_in(self, now: datetime) -> bool:
        if self.password_hash is None or self.disabled_at is not None:
            return False
        return self.expires_at is None or now < self.expires_at


@dataclass(frozen=True)
class Principal:
    """Who a valid access token says the caller is."""

    account_id: UUID
    role: ResearchRole


class SessionState(Enum):
    ACTIVE = "active"
    REUSED = "reused"
    EXPIRED = "expired"


@dataclass(frozen=True)
class RefreshSession:
    """One refresh token. Each use rotates it; every token of a sign-in shares the family."""

    id: UUID
    account_id: UUID
    family_id: UUID
    token_hash: str
    expires_at: datetime
    used_at: datetime | None = None
    revoked_at: datetime | None = None

    def state(self, now: datetime) -> SessionState:
        if self.used_at is not None or self.revoked_at is not None:
            return SessionState.REUSED
        if now >= self.expires_at:
            return SessionState.EXPIRED
        return SessionState.ACTIVE


def validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise WeakPasswordError(f"Password must have at least {MIN_PASSWORD_LENGTH} characters")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def can_run_study(role: ResearchRole) -> bool:
    return role is ResearchRole.ADMIN


def new_secret() -> str:
    """Opaque token for refresh sessions and invite links."""
    return secrets.token_urlsafe(32)


def hash_secret(raw: str) -> str:
    # The tokens are 256-bit random values, so a fast hash is enough: there is nothing
    # to brute-force.
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


@dataclass(frozen=True)
class LoginLimits:
    per_account: int
    per_ip: int
    window_seconds: int


class LoginThrottle:
    """Caps sign-in attempts per account and per IP in a fixed window (Redis counters)."""

    def __init__(self, store: QuotaStore, limits: LoginLimits) -> None:
        self._store = store
        self._limits = limits

    async def register_attempt(self, email: str, ip: str) -> None:
        window = self._limits.window_seconds
        account_count = await self._store.increment(f"login:account:{hash_secret(email)}", window)
        ip_count = await self._store.increment(f"login:ip:{ip}", window)
        if account_count > self._limits.per_account or ip_count > self._limits.per_ip:
            raise TooManyAttemptsError(retry_after_seconds=window)
