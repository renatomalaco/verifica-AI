from datetime import datetime, timedelta, timezone

import pytest

from scan_orchestrator.domain.device_token import issue_device_token, verify_device_token
from scan_orchestrator.domain.quota import ExplainQuota, QuotaExceededError, QuotaLimits
from scan_orchestrator.infrastructure.quota_store import InMemoryQuotaStore

SECRET = b"segredo-de-teste"
# 16/10/2026 15:00 in Brasília (UTC-3)
NOON_UTC = datetime(2026, 10, 16, 18, 0, tzinfo=timezone.utc)


class Clock:
    def __init__(self, now: datetime):
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def make_quota(daily=3, monthly=30, ip_limit=100, ip_window=3600, now=NOON_UTC):
    store = InMemoryQuotaStore()
    clock = Clock(now)
    quota = ExplainQuota(
        store=store,
        limits=QuotaLimits(daily=daily, monthly=monthly, ip_per_window=ip_limit, ip_window_seconds=ip_window),
        utc_offset_hours=-3,
        clock=clock,
    )
    return quota, store, clock


# --- Device token ---

def test_device_token_roundtrip():
    device_id, token = issue_device_token(SECRET)
    assert verify_device_token(token, SECRET) == device_id


@pytest.mark.parametrize("bad", [None, "", "sem-ponto", "nao-e-uuid.abc", "a.b.c"])
def test_device_token_rejects_garbage(bad):
    assert verify_device_token(bad, SECRET) is None


def test_device_token_rejects_tampered_id_and_other_secret():
    device_id, token = issue_device_token(SECRET)
    _, signature = token.split(".")
    _, other_token = issue_device_token(SECRET)
    other_id = other_token.split(".")[0]

    assert verify_device_token(f"{other_id}.{signature}", SECRET) is None
    assert verify_device_token(token, b"outro-segredo") is None


# --- Quota ---

async def test_counts_down_remaining_and_uses_documented_keys():
    quota, store, _ = make_quota(daily=3)

    first = await quota.consume("dev-1", "1.2.3.4")
    second = await quota.consume("dev-1", "1.2.3.4")

    assert (first.remaining_today, second.remaining_today) == (2, 1)
    assert store.counters["quota:dev-1:20261016"] == 2
    assert store.counters["quota:dev-1:202610"] == 2


async def test_daily_limit_returns_next_local_midnight():
    quota, _, _ = make_quota(daily=2)
    await quota.consume("dev-1", "ip")
    await quota.consume("dev-1", "ip")

    with pytest.raises(QuotaExceededError) as exc:
        await quota.consume("dev-1", "ip")

    # 17/10 00:00 in Brasília = 03:00 UTC
    assert exc.value.retry_at == datetime(2026, 10, 17, 3, 0, tzinfo=timezone.utc)


async def test_denied_attempt_does_not_consume_quota():
    quota, store, _ = make_quota(daily=1)
    await quota.consume("dev-1", "ip")
    for _ in range(3):
        with pytest.raises(QuotaExceededError):
            await quota.consume("dev-1", "ip")

    assert store.counters["quota:dev-1:20261016"] == 1
    assert store.counters["quota:dev-1:202610"] == 1


async def test_new_local_day_resets_daily_count():
    quota, _, clock = make_quota(daily=1)
    await quota.consume("dev-1", "ip")
    clock.now = datetime(2026, 10, 17, 3, 0, tzinfo=timezone.utc)

    grant = await quota.consume("dev-1", "ip")
    assert grant.remaining_today == 0


async def test_local_date_is_used_for_keys_near_midnight():
    # 17/10 01:30 UTC is still 16/10 in Brasília
    quota, store, _ = make_quota(now=datetime(2026, 10, 17, 1, 30, tzinfo=timezone.utc))
    await quota.consume("dev-1", "ip")
    assert "quota:dev-1:20261016" in store.counters


async def test_monthly_limit_returns_first_day_of_next_month():
    quota, _, clock = make_quota(daily=5, monthly=2)
    await quota.consume("dev-1", "ip")
    clock.now += timedelta(days=1)
    await quota.consume("dev-1", "ip")
    clock.now += timedelta(days=1)

    with pytest.raises(QuotaExceededError) as exc:
        await quota.consume("dev-1", "ip")

    assert exc.value.retry_at == datetime(2026, 11, 1, 3, 0, tzinfo=timezone.utc)


async def test_remaining_today_respects_monthly_ceiling():
    quota, _, _ = make_quota(daily=5, monthly=2)
    grant = await quota.consume("dev-1", "ip")
    assert grant.remaining_today == 1


async def test_ip_ceiling_blocks_many_devices_behind_same_ip():
    quota, _, clock = make_quota(daily=10, ip_limit=2, ip_window=600)
    await quota.consume("dev-1", "9.9.9.9")
    clock.now += timedelta(seconds=60)
    await quota.consume("dev-2", "9.9.9.9")

    with pytest.raises(QuotaExceededError) as exc:
        await quota.consume("dev-3", "9.9.9.9")

    # Released once the first call leaves the sliding window.
    assert exc.value.retry_at == NOON_UTC + timedelta(seconds=600)
    # Another IP remains free.
    await quota.consume("dev-3", "8.8.8.8")


async def test_ip_window_slides():
    quota, _, clock = make_quota(daily=10, ip_limit=1, ip_window=600)
    await quota.consume("dev-1", "9.9.9.9")
    clock.now += timedelta(seconds=601)
    await quota.consume("dev-2", "9.9.9.9")


async def test_refund_gives_the_explanation_back():
    quota, store, _ = make_quota(daily=1, ip_limit=1)
    grant = await quota.consume("dev-1", "ip")
    await quota.refund(grant)

    again = await quota.consume("dev-1", "ip")
    assert again.remaining_today == 0
    assert store.counters["quota:dev-1:20261016"] == 1
