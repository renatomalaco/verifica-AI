from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest

from contracts import ResearchAccountStatus, ResearchRole
from scan_orchestrator.domain.research_access import (
    Account,
    LoginLimits,
    LoginThrottle,
    RefreshSession,
    SessionState,
    TooManyAttemptsError,
    WeakPasswordError,
    access_ends_at,
    can_manage_accounts,
    can_run_study,
    hash_secret,
    invite_link,
    new_secret,
    validate_password,
)
from scan_orchestrator.infrastructure.quota_store import InMemoryQuotaStore

NOW = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)


def account(**overrides) -> Account:
    fields = {
        "id": uuid4(),
        "email": "banca@exemplo.com",
        "role": ResearchRole.RESEARCHER,
        "password_hash": "$argon2id$hash",
    }
    return Account(**(fields | overrides))


def test_an_account_with_a_password_can_sign_in():
    assert account().can_sign_in(NOW)


def test_an_invited_account_without_a_password_cannot_sign_in():
    assert not account(password_hash=None).can_sign_in(NOW)


def test_an_expired_account_cannot_sign_in():
    assert not account(expires_at=NOW - timedelta(seconds=1)).can_sign_in(NOW)
    assert account(expires_at=NOW + timedelta(days=7)).can_sign_in(NOW)


def test_a_disabled_account_cannot_sign_in():
    assert not account(disabled_at=NOW - timedelta(hours=1)).can_sign_in(NOW)


def test_passwords_need_at_least_twelve_characters():
    with pytest.raises(WeakPasswordError):
        validate_password("onze-letras")
    validate_password("doze-letras!")


def test_only_the_admin_runs_the_study():
    assert can_run_study(ResearchRole.ADMIN)
    assert not can_run_study(ResearchRole.RESEARCHER)


def test_secrets_are_random_and_stored_only_as_hash():
    raw = new_secret()

    assert raw != new_secret()
    assert len(raw) >= 43  # 32 random bytes
    assert hash_secret(raw) == hash_secret(raw)
    assert raw not in hash_secret(raw)


def session(**overrides) -> RefreshSession:
    fields = {
        "id": uuid4(),
        "account_id": uuid4(),
        "family_id": uuid4(),
        "token_hash": hash_secret("refresh"),
        "expires_at": NOW + timedelta(days=7),
    }
    return RefreshSession(**(fields | overrides))


def test_an_unused_refresh_session_is_active():
    assert session().state(NOW) is SessionState.ACTIVE


def test_a_used_or_revoked_refresh_session_signals_reuse():
    # Presenting an already rotated token means a copy exists somewhere else: treat it as theft.
    assert session(used_at=NOW).state(NOW) is SessionState.REUSED
    assert session(revoked_at=NOW).state(NOW) is SessionState.REUSED


def test_an_expired_refresh_session_is_expired():
    assert session(expires_at=NOW).state(NOW) is SessionState.EXPIRED


LIMITS = LoginLimits(per_account=3, per_ip=5, window_seconds=900)


async def test_login_attempts_per_account_are_capped():
    store = InMemoryQuotaStore()
    throttle = LoginThrottle(store, LIMITS)
    for _ in range(3):
        await throttle.register_attempt("banca@exemplo.com", ip="10.0.0.1")

    with pytest.raises(TooManyAttemptsError) as exc:
        await throttle.register_attempt("banca@exemplo.com", ip="10.0.0.2")
    assert exc.value.retry_after_seconds == 900


async def test_login_attempts_per_ip_are_capped_across_accounts():
    throttle = LoginThrottle(InMemoryQuotaStore(), LIMITS)
    for n in range(5):
        await throttle.register_attempt(f"conta{n}@exemplo.com", ip="10.0.0.1")

    with pytest.raises(TooManyAttemptsError):
        await throttle.register_attempt("outra@exemplo.com", ip="10.0.0.1")


async def test_the_throttle_never_stores_the_email_in_clear():
    store = InMemoryQuotaStore()
    await LoginThrottle(store, LIMITS).register_attempt("banca@exemplo.com", ip="10.0.0.1")

    assert not any("banca" in key for key in store.counters)


@pytest.mark.parametrize(
    ("overrides", "status"),
    [
        ({}, ResearchAccountStatus.ACTIVE),
        ({"password_hash": None}, ResearchAccountStatus.INVITED),
        ({"expires_at": NOW - timedelta(seconds=1)}, ResearchAccountStatus.EXPIRED),
        ({"disabled_at": NOW}, ResearchAccountStatus.DISABLED),
        # Blocking wins: an old invite or an expiry must not hide that someone was cut off.
        (
            {"password_hash": None, "expires_at": NOW - timedelta(days=1), "disabled_at": NOW},
            ResearchAccountStatus.DISABLED,
        ),
    ],
)
def test_the_admin_sees_one_status_per_account(overrides, status):
    assert account(**overrides).status(NOW) is status


def test_only_the_admin_manages_accounts():
    assert can_manage_accounts(ResearchRole.ADMIN)
    assert not can_manage_accounts(ResearchRole.RESEARCHER)


def test_access_ends_at_midnight_after_the_last_day_in_brasilia():
    assert access_ends_at(date(2026, 12, 20)) == datetime(2026, 12, 21, 3, 0, tzinfo=timezone.utc)


def test_the_invite_link_carries_the_token_after_the_hash():
    assert (
        invite_link("https://verifica.test", "abc")
        == "https://verifica.test/pesquisa/convite#token=abc"
    )
