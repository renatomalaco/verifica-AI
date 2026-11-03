from dataclasses import replace
from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, ForeignKey, String, Table, Text, select, update
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.dialects.postgresql import insert

from contracts import ResearchRole
from scan_orchestrator.domain.research_access import Account, RefreshSession
from scan_orchestrator.infrastructure.scan_repository import metadata


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


contas_pesquisa_table = Table(
    "contas_pesquisa",
    metadata,
    Column("id", PG_UUID(as_uuid=True), primary_key=True),
    Column("email", String(254), nullable=False, unique=True),
    Column("role", String(20), nullable=False),
    Column("password_hash", Text, nullable=True),
    Column("expires_at", DateTime(timezone=True), nullable=True),
    Column("disabled_at", DateTime(timezone=True), nullable=True),
    Column("invite_hash", String(64), nullable=True, unique=True),
    Column("invite_expires_at", DateTime(timezone=True), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, default=_utcnow),
)

sessoes_pesquisa_table = Table(
    "sessoes_pesquisa",
    metadata,
    Column("id", PG_UUID(as_uuid=True), primary_key=True),
    Column("account_id", PG_UUID(as_uuid=True), ForeignKey("contas_pesquisa.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("family_id", PG_UUID(as_uuid=True), nullable=False, index=True),
    Column("token_hash", String(64), nullable=False, unique=True),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("used_at", DateTime(timezone=True), nullable=True),
    Column("revoked_at", DateTime(timezone=True), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, default=_utcnow),
)


class ResearchAccountRepository(Protocol):
    async def get_account(self, account_id: UUID) -> Account | None: ...

    async def find_by_email(self, email: str) -> Account | None: ...

    async def find_by_invite(self, invite_hash: str) -> Account | None: ...

    async def save_invite(
        self,
        email: str,
        role: ResearchRole,
        expires_at: datetime | None,
        invite_hash: str,
        invite_expires_at: datetime,
    ) -> Account:
        """Creates the account, or renews the invite (and access) of an existing one."""
        ...

    async def set_password(self, account_id: UUID, password_hash: str) -> None:
        """Stores the password and consumes the invite."""
        ...

    async def disable(self, account_id: UUID, now: datetime) -> None: ...

    async def add_session(self, session: RefreshSession) -> None: ...

    async def find_session(self, token_hash: str) -> RefreshSession | None: ...

    async def mark_used(self, session_id: UUID, now: datetime) -> bool:
        """True only for the first use; a concurrent second use gets False."""
        ...

    async def revoke_family(self, family_id: UUID, now: datetime) -> None: ...

    async def revoke_account_sessions(self, account_id: UUID, now: datetime) -> None: ...


class InMemoryResearchAccountRepository:
    """In-memory implementation for tests and development without Postgres."""

    def __init__(self) -> None:
        self._accounts: dict[UUID, Account] = {}
        self._sessions: dict[UUID, RefreshSession] = {}

    async def get_account(self, account_id: UUID) -> Account | None:
        return self._accounts.get(account_id)

    async def find_by_email(self, email: str) -> Account | None:
        return next((a for a in self._accounts.values() if a.email == email), None)

    async def find_by_invite(self, invite_hash: str) -> Account | None:
        return next((a for a in self._accounts.values() if a.invite_hash == invite_hash), None)

    async def save_invite(self, email, role, expires_at, invite_hash, invite_expires_at) -> Account:
        existing = await self.find_by_email(email)
        base = existing or Account(id=uuid4(), email=email, role=role, password_hash=None)
        account = replace(
            base,
            role=role,
            expires_at=expires_at,
            disabled_at=None,
            invite_hash=invite_hash,
            invite_expires_at=invite_expires_at,
        )
        self._accounts[account.id] = account
        return account

    async def set_password(self, account_id: UUID, password_hash: str) -> None:
        account = self._accounts[account_id]
        self._accounts[account_id] = replace(
            account, password_hash=password_hash, invite_hash=None, invite_expires_at=None
        )

    async def disable(self, account_id: UUID, now: datetime) -> None:
        self._accounts[account_id] = replace(self._accounts[account_id], disabled_at=now)

    async def add_session(self, session: RefreshSession) -> None:
        self._sessions[session.id] = session

    async def find_session(self, token_hash: str) -> RefreshSession | None:
        return next((s for s in self._sessions.values() if s.token_hash == token_hash), None)

    async def mark_used(self, session_id: UUID, now: datetime) -> bool:
        session = self._sessions[session_id]
        if session.used_at is not None:
            return False
        self._sessions[session_id] = replace(session, used_at=now)
        return True

    async def revoke_family(self, family_id: UUID, now: datetime) -> None:
        self._revoke_where(lambda s: s.family_id == family_id, now)

    async def revoke_account_sessions(self, account_id: UUID, now: datetime) -> None:
        self._revoke_where(lambda s: s.account_id == account_id, now)

    def _revoke_where(self, matches, now: datetime) -> None:
        for session_id, session in self._sessions.items():
            if matches(session) and session.revoked_at is None:
                self._sessions[session_id] = replace(session, revoked_at=now)


def _account(row) -> Account:
    return Account(
        id=row["id"],
        email=row["email"],
        role=ResearchRole(row["role"]),
        password_hash=row["password_hash"],
        expires_at=row["expires_at"],
        disabled_at=row["disabled_at"],
        invite_hash=row["invite_hash"],
        invite_expires_at=row["invite_expires_at"],
    )


def _session(row) -> RefreshSession:
    return RefreshSession(
        id=row["id"],
        account_id=row["account_id"],
        family_id=row["family_id"],
        token_hash=row["token_hash"],
        expires_at=row["expires_at"],
        used_at=row["used_at"],
        revoked_at=row["revoked_at"],
    )


class SqlResearchAccountRepository:
    """PostgreSQL implementation. Passwords and tokens are stored only as hashes."""

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    async def _one(self, stmt):
        async with self._session_factory() as session:
            return (await session.execute(stmt)).mappings().first()

    async def _write(self, stmt):
        async with self._session_factory() as session:
            async with session.begin():
                return await session.execute(stmt)

    async def get_account(self, account_id: UUID) -> Account | None:
        row = await self._one(select(contas_pesquisa_table).where(contas_pesquisa_table.c.id == account_id))
        return _account(row) if row else None

    async def find_by_email(self, email: str) -> Account | None:
        row = await self._one(select(contas_pesquisa_table).where(contas_pesquisa_table.c.email == email))
        return _account(row) if row else None

    async def find_by_invite(self, invite_hash: str) -> Account | None:
        row = await self._one(select(contas_pesquisa_table).where(contas_pesquisa_table.c.invite_hash == invite_hash))
        return _account(row) if row else None

    async def save_invite(self, email, role, expires_at, invite_hash, invite_expires_at) -> Account:
        renewed = {
            "role": role.value,
            "expires_at": expires_at,
            "disabled_at": None,
            "invite_hash": invite_hash,
            "invite_expires_at": invite_expires_at,
        }
        stmt = (
            insert(contas_pesquisa_table)
            .values(id=uuid4(), email=email, created_at=_utcnow(), **renewed)
            .on_conflict_do_update(index_elements=["email"], set_=renewed)
            .returning(*contas_pesquisa_table.c)
        )
        return _account((await self._write(stmt)).mappings().one())

    async def set_password(self, account_id: UUID, password_hash: str) -> None:
        await self._write(
            update(contas_pesquisa_table)
            .where(contas_pesquisa_table.c.id == account_id)
            .values(password_hash=password_hash, invite_hash=None, invite_expires_at=None)
        )

    async def disable(self, account_id: UUID, now: datetime) -> None:
        await self._write(
            update(contas_pesquisa_table).where(contas_pesquisa_table.c.id == account_id).values(disabled_at=now)
        )

    async def add_session(self, session: RefreshSession) -> None:
        await self._write(
            sessoes_pesquisa_table.insert().values(
                id=session.id,
                account_id=session.account_id,
                family_id=session.family_id,
                token_hash=session.token_hash,
                expires_at=session.expires_at,
                created_at=_utcnow(),
            )
        )

    async def find_session(self, token_hash: str) -> RefreshSession | None:
        row = await self._one(select(sessoes_pesquisa_table).where(sessoes_pesquisa_table.c.token_hash == token_hash))
        return _session(row) if row else None

    async def mark_used(self, session_id: UUID, now: datetime) -> bool:
        # The "used_at IS NULL" guard makes the check and the write one atomic step.
        result = await self._write(
            update(sessoes_pesquisa_table)
            .where(sessoes_pesquisa_table.c.id == session_id, sessoes_pesquisa_table.c.used_at.is_(None))
            .values(used_at=now)
        )
        return result.rowcount == 1

    async def revoke_family(self, family_id: UUID, now: datetime) -> None:
        await self._revoke(sessoes_pesquisa_table.c.family_id == family_id, now)

    async def revoke_account_sessions(self, account_id: UUID, now: datetime) -> None:
        await self._revoke(sessoes_pesquisa_table.c.account_id == account_id, now)

    async def _revoke(self, condition, now: datetime) -> None:
        await self._write(
            update(sessoes_pesquisa_table)
            .where(condition, sessoes_pesquisa_table.c.revoked_at.is_(None))
            .values(revoked_at=now)
        )
