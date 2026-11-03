import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from contracts import ResearchRole
from scan_orchestrator.domain.research_access import RefreshSession, hash_secret
from scan_orchestrator.infrastructure.research_account_repository import (
    InMemoryResearchAccountRepository,
    SqlResearchAccountRepository,
)
from scan_orchestrator.infrastructure.scan_repository import metadata

DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")
NOW = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)


@pytest.fixture(params=["memory", pytest.param("sql", marks=pytest.mark.integration)])
async def repo(request):
    if request.param == "memory":
        yield InMemoryResearchAccountRepository()
        return
    if not DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set (needs the Postgres from infra/docker-compose.yml)")
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    yield SqlResearchAccountRepository(async_sessionmaker(engine, expire_on_commit=False))
    await engine.dispose()


def unique_email() -> str:
    return f"pesquisa-{uuid4().hex[:8]}@exemplo.com"


async def invite(repo, email: str, invite_secret: str = "convite"):
    return await repo.save_invite(
        email=email,
        role=ResearchRole.RESEARCHER,
        expires_at=NOW + timedelta(days=30),
        invite_hash=hash_secret(invite_secret + email),
        invite_expires_at=NOW + timedelta(hours=48),
    )


async def test_an_invited_account_is_found_by_email_and_invite(repo):
    email = unique_email()
    account = await invite(repo, email)

    assert (await repo.find_by_email(email)) == account
    assert (await repo.find_by_invite(hash_secret("convite" + email))) == account
    assert account.password_hash is None
    assert account.role is ResearchRole.RESEARCHER


async def test_inviting_the_same_email_again_updates_the_account(repo):
    email = unique_email()
    first = await invite(repo, email, "primeiro")
    again = await repo.save_invite(
        email=email,
        role=ResearchRole.ADMIN,
        expires_at=None,
        invite_hash=hash_secret("segundo" + email),
        invite_expires_at=NOW + timedelta(hours=48),
    )

    assert again.id == first.id
    assert again.role is ResearchRole.ADMIN
    assert again.expires_at is None
    assert await repo.find_by_invite(hash_secret("primeiro" + email)) is None


async def test_setting_the_password_consumes_the_invite(repo):
    email = unique_email()
    account = await invite(repo, email)

    await repo.set_password(account.id, "$argon2id$hash")

    stored = await repo.get_account(account.id)
    assert stored.password_hash == "$argon2id$hash"
    assert stored.invite_hash is None
    assert await repo.find_by_invite(hash_secret("convite" + email)) is None


async def test_a_disabled_account_keeps_the_disable_time(repo):
    account = await invite(repo, unique_email())

    await repo.disable(account.id, NOW)

    assert (await repo.get_account(account.id)).disabled_at == NOW


async def new_session(repo, account_id, family_id=None) -> RefreshSession:
    session = RefreshSession(
        id=uuid4(),
        account_id=account_id,
        family_id=family_id or uuid4(),
        token_hash=hash_secret(uuid4().hex),
        expires_at=NOW + timedelta(days=7),
    )
    await repo.add_session(session)
    return session


async def test_a_session_is_used_only_once(repo):
    account = await invite(repo, unique_email())
    session = await new_session(repo, account.id)

    assert await repo.find_session(session.token_hash) == session
    assert await repo.mark_used(session.id, NOW) is True
    assert await repo.mark_used(session.id, NOW) is False  # a concurrent second use loses
    assert (await repo.find_session(session.token_hash)).used_at == NOW


async def test_revoking_a_family_leaves_other_sign_ins_alone(repo):
    account = await invite(repo, unique_email())
    family = uuid4()
    rotated = await new_session(repo, account.id, family)
    current = await new_session(repo, account.id, family)
    other_device = await new_session(repo, account.id)

    await repo.revoke_family(family, NOW)

    assert (await repo.find_session(rotated.token_hash)).revoked_at == NOW
    assert (await repo.find_session(current.token_hash)).revoked_at == NOW
    assert (await repo.find_session(other_device.token_hash)).revoked_at is None


async def test_revoking_an_account_ends_all_its_sessions(repo):
    account = await invite(repo, unique_email())
    first = await new_session(repo, account.id)
    second = await new_session(repo, account.id)

    await repo.revoke_account_sessions(account.id, NOW)

    assert (await repo.find_session(first.token_hash)).revoked_at == NOW
    assert (await repo.find_session(second.token_hash)).revoked_at == NOW
