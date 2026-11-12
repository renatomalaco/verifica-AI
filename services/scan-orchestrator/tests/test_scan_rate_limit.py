from datetime import datetime, timedelta, timezone

import pytest

from scan_orchestrator.domain.scan_rate_limit import (
    ScanRateLimit,
    ScanRateLimitedError,
    ScanRateLimits,
)
from scan_orchestrator.infrastructure.quota_store import InMemoryQuotaStore

START = datetime(2026, 11, 10, 15, 0, tzinfo=timezone.utc)


class Clock:
    def __init__(self, now: datetime):
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def make_limit(per_ip=2, window=60):
    clock = Clock(START)
    store = InMemoryQuotaStore()
    limit = ScanRateLimit(store, ScanRateLimits(per_ip=per_ip, window_seconds=window), clock=clock)
    return limit, store, clock


async def test_allows_scans_up_to_the_limit():
    limit, _, _ = make_limit(per_ip=2)

    await limit.check("200.1.1.1")
    await limit.check("200.1.1.1")


async def test_blocks_the_next_scan_and_says_when_the_oldest_one_leaves_the_window():
    limit, _, clock = make_limit(per_ip=2, window=60)
    await limit.check("200.1.1.1")
    clock.now = START + timedelta(seconds=10)
    await limit.check("200.1.1.1")

    with pytest.raises(ScanRateLimitedError) as exc:
        await limit.check("200.1.1.1")

    assert exc.value.retry_at == START + timedelta(seconds=60)


async def test_each_ip_has_its_own_window():
    limit, _, _ = make_limit(per_ip=1)
    await limit.check("200.1.1.1")

    await limit.check("200.2.2.2")


async def test_denied_scans_do_not_extend_the_wait():
    limit, store, clock = make_limit(per_ip=1, window=60)
    await limit.check("200.1.1.1")
    for _ in range(5):
        with pytest.raises(ScanRateLimitedError):
            await limit.check("200.1.1.1")

    assert len(store.windows["scan:ip:200.1.1.1"]) == 1
    clock.now = START + timedelta(seconds=60)
    await limit.check("200.1.1.1")
