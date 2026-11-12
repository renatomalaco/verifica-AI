from datetime import datetime, timezone

import pytest

from contracts import ResearchRole
from scan_orchestrator.application.research_auth import ResearchAuth
from scan_orchestrator.domain.research_access import LoginLimits, LoginThrottle
from scan_orchestrator.infrastructure.access_tokens import AccessTokenIssuer, generate_key_pair
from scan_orchestrator.infrastructure.passwords import PasswordHasher
from scan_orchestrator.infrastructure.quota_store import InMemoryQuotaStore
from scan_orchestrator.infrastructure.research_account_repository import (
    InMemoryResearchAccountRepository,
)
from scan_orchestrator.research_cli import parse_args, run

BASE_URL = "https://verifica.test"


@pytest.fixture
def repo() -> InMemoryResearchAccountRepository:
    return InMemoryResearchAccountRepository()


@pytest.fixture
def auth(repo) -> ResearchAuth:
    return ResearchAuth(
        repository=repo,
        hasher=PasswordHasher(),
        issuer=AccessTokenIssuer(generate_key_pair()[0]),
        throttle=LoginThrottle(
            InMemoryQuotaStore(), LoginLimits(per_account=9, per_ip=9, window_seconds=60)
        ),
    )


async def test_keygen_prints_both_keys_as_env_lines():
    output = await run(parse_args(["keygen"]), auth=None, base_url=BASE_URL)

    lines = output.splitlines()
    assert lines[0].startswith("AUTH_JWT_PRIVATE_KEY=")
    assert lines[1].startswith("AUTH_JWT_PUBLIC_KEY=")


async def test_invite_prints_a_one_time_link_in_the_fragment(auth, repo):
    output = await run(
        parse_args(["invite", "--email", "banca@exemplo.com"]), auth=auth, base_url=BASE_URL
    )

    # The token travels after "#", so it never reaches server logs or Referer headers.
    assert f"{BASE_URL}/pesquisa/convite#token=" in output
    token = output.split("#token=")[1].split()[0]
    await auth.accept_invite(token, "senha-da-banca-2026")
    account = await repo.find_by_email("banca@exemplo.com")
    assert account.role is ResearchRole.RESEARCHER
    assert account.expires_at is None


async def test_invite_with_role_and_expiry_ends_after_that_day_in_brasilia(auth, repo):
    await run(
        parse_args(
            [
                "invite",
                "--email",
                "admin@exemplo.com",
                "--role",
                "admin",
                "--expires-on",
                "2026-12-20",
            ]
        ),
        auth=auth,
        base_url=BASE_URL,
    )

    account = await repo.find_by_email("admin@exemplo.com")
    assert account.role is ResearchRole.ADMIN
    assert account.expires_at == datetime(
        2026, 12, 21, 3, 0, tzinfo=timezone.utc
    )  # midnight in Brasília


async def test_disable_reports_whether_the_account_existed(auth):
    await run(parse_args(["invite", "--email", "banca@exemplo.com"]), auth=auth, base_url=BASE_URL)

    assert "blocked" in await run(
        parse_args(["disable", "--email", "banca@exemplo.com"]), auth=auth, base_url=BASE_URL
    )
    assert "not found" in await run(
        parse_args(["disable", "--email", "ninguem@exemplo.com"]), auth=auth, base_url=BASE_URL
    )


def test_an_unknown_role_is_rejected():
    with pytest.raises(SystemExit):
        parse_args(["invite", "--email", "x@exemplo.com", "--role", "root"])
