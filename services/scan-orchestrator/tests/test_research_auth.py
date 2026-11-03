from datetime import datetime, timedelta, timezone

import pytest

from contracts import ResearchRole
from scan_orchestrator.application.research_auth import (
    InvalidCredentialsError,
    InviteInvalidError,
    ResearchAuth,
    SessionRejectedError,
)
from scan_orchestrator.domain.research_access import (
    LoginLimits,
    LoginThrottle,
    TooManyAttemptsError,
    WeakPasswordError,
)
from scan_orchestrator.infrastructure.access_tokens import AccessTokenIssuer, AccessTokenVerifier, generate_key_pair
from scan_orchestrator.infrastructure.passwords import PasswordHasher
from scan_orchestrator.infrastructure.quota_store import InMemoryQuotaStore
from scan_orchestrator.infrastructure.research_account_repository import InMemoryResearchAccountRepository

PRIVATE_KEY, PUBLIC_KEY = generate_key_pair()
PASSWORD = "senha-da-banca-2026"
HASHER = PasswordHasher()  # argon2 is deliberately slow: build it once


class Clock:
    def __init__(self) -> None:
        self.now = datetime.now(timezone.utc)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **delta) -> None:
        self.now += timedelta(**delta)


@pytest.fixture
def clock() -> Clock:
    return Clock()


def build_auth(clock: Clock, per_account: int = 100) -> ResearchAuth:
    return ResearchAuth(
        repository=InMemoryResearchAccountRepository(),
        hasher=HASHER,
        issuer=AccessTokenIssuer(PRIVATE_KEY, clock=clock),
        throttle=LoginThrottle(InMemoryQuotaStore(), LoginLimits(per_account=per_account, per_ip=100, window_seconds=900)),
        clock=clock,
    )


@pytest.fixture
def auth(clock) -> ResearchAuth:
    return build_auth(clock)


async def researcher(auth: ResearchAuth, email: str = "banca@exemplo.com", expires_at=None) -> None:
    token = await auth.invite(email, ResearchRole.RESEARCHER, expires_at=expires_at)
    await auth.accept_invite(token, PASSWORD)


async def test_an_accepted_invite_lets_the_researcher_sign_in(auth):
    await researcher(auth)

    signed_in = await auth.login("banca@exemplo.com", PASSWORD, ip="10.0.0.1")

    principal = AccessTokenVerifier(PUBLIC_KEY).verify(signed_in.access_token)
    assert principal.role is ResearchRole.RESEARCHER
    assert principal.account_id == signed_in.account.id
    assert signed_in.refresh_token


async def test_the_invite_link_works_only_once(auth):
    token = await auth.invite("banca@exemplo.com", ResearchRole.RESEARCHER)
    await auth.accept_invite(token, PASSWORD)

    with pytest.raises(InviteInvalidError):
        await auth.accept_invite(token, "outra-senha-bem-longa")


async def test_the_invite_link_expires_after_48_hours(auth, clock):
    token = await auth.invite("banca@exemplo.com", ResearchRole.RESEARCHER)
    clock.advance(hours=48, seconds=1)

    with pytest.raises(InviteInvalidError):
        await auth.accept_invite(token, PASSWORD)


async def test_an_unknown_invite_is_rejected(auth):
    with pytest.raises(InviteInvalidError):
        await auth.accept_invite("inventado", PASSWORD)


async def test_a_short_password_is_refused_and_the_invite_stays_valid(auth):
    token = await auth.invite("banca@exemplo.com", ResearchRole.RESEARCHER)

    with pytest.raises(WeakPasswordError):
        await auth.accept_invite(token, "curta")
    await auth.accept_invite(token, PASSWORD)


@pytest.mark.parametrize("email, password", [("banca@exemplo.com", "senha-errada-qualquer"), ("ninguem@exemplo.com", PASSWORD)])
async def test_wrong_password_and_unknown_email_fail_the_same_way(auth, email, password):
    await researcher(auth)

    with pytest.raises(InvalidCredentialsError):
        await auth.login(email, password, ip="10.0.0.1")


async def test_an_expired_account_cannot_sign_in(auth, clock):
    await researcher(auth, expires_at=clock.now + timedelta(days=7))
    clock.advance(days=7)

    with pytest.raises(InvalidCredentialsError):
        await auth.login("banca@exemplo.com", PASSWORD, ip="10.0.0.1")


async def test_repeated_attempts_are_throttled(clock):
    auth = build_auth(clock, per_account=2)
    await researcher(auth)
    for _ in range(2):
        with pytest.raises(InvalidCredentialsError):
            await auth.login("banca@exemplo.com", "senha-errada-qualquer", ip="10.0.0.1")

    with pytest.raises(TooManyAttemptsError):
        await auth.login("banca@exemplo.com", PASSWORD, ip="10.0.0.1")


async def test_refresh_rotates_the_token(auth):
    await researcher(auth)
    first = await auth.login("banca@exemplo.com", PASSWORD, ip="10.0.0.1")

    second = await auth.refresh(first.refresh_token)

    assert second.refresh_token != first.refresh_token
    assert AccessTokenVerifier(PUBLIC_KEY).verify(second.access_token).account_id == first.account.id


async def test_reusing_an_old_refresh_revokes_the_whole_sign_in(auth):
    await researcher(auth)
    stolen = await auth.login("banca@exemplo.com", PASSWORD, ip="10.0.0.1")
    legit = await auth.refresh(stolen.refresh_token)

    with pytest.raises(SessionRejectedError):
        await auth.refresh(stolen.refresh_token)
    with pytest.raises(SessionRejectedError):
        await auth.refresh(legit.refresh_token)


async def test_a_refresh_token_lasts_seven_days(auth, clock):
    await researcher(auth)
    signed_in = await auth.login("banca@exemplo.com", PASSWORD, ip="10.0.0.1")
    clock.advance(days=7)

    with pytest.raises(SessionRejectedError):
        await auth.refresh(signed_in.refresh_token)


async def test_refresh_stops_when_the_account_expires(auth, clock):
    await researcher(auth, expires_at=clock.now + timedelta(days=1))
    signed_in = await auth.login("banca@exemplo.com", PASSWORD, ip="10.0.0.1")
    clock.advance(days=1)

    with pytest.raises(SessionRejectedError):
        await auth.refresh(signed_in.refresh_token)


@pytest.mark.parametrize("token", ["", "inventado"])
async def test_an_unknown_refresh_is_rejected(auth, token):
    with pytest.raises(SessionRejectedError):
        await auth.refresh(token)


async def test_logout_ends_the_sign_in(auth):
    await researcher(auth)
    signed_in = await auth.login("banca@exemplo.com", PASSWORD, ip="10.0.0.1")

    await auth.logout(signed_in.refresh_token)

    with pytest.raises(SessionRejectedError):
        await auth.refresh(signed_in.refresh_token)


async def test_logout_with_an_unknown_token_is_harmless(auth):
    await auth.logout("inventado")


async def test_disabling_an_account_blocks_login_and_refresh(auth):
    await researcher(auth)
    signed_in = await auth.login("banca@exemplo.com", PASSWORD, ip="10.0.0.1")

    assert await auth.disable("banca@exemplo.com") is True

    with pytest.raises(SessionRejectedError):
        await auth.refresh(signed_in.refresh_token)
    with pytest.raises(InvalidCredentialsError):
        await auth.login("banca@exemplo.com", PASSWORD, ip="10.0.0.1")


async def test_disabling_an_unknown_account_reports_it(auth):
    assert await auth.disable("ninguem@exemplo.com") is False


async def test_current_account_only_while_it_can_sign_in(auth, clock):
    await researcher(auth, expires_at=clock.now + timedelta(days=1))
    signed_in = await auth.login("banca@exemplo.com", PASSWORD, ip="10.0.0.1")

    assert (await auth.current_account(signed_in.account.id)).email == "banca@exemplo.com"
    clock.advance(days=1)
    assert await auth.current_account(signed_in.account.id) is None


async def test_invite_normalizes_the_email(auth):
    token = await auth.invite("  Banca@Exemplo.com ", ResearchRole.RESEARCHER)
    await auth.accept_invite(token, PASSWORD)

    assert (await auth.login("banca@exemplo.com", PASSWORD, ip="10.0.0.1")).account.email == "banca@exemplo.com"
