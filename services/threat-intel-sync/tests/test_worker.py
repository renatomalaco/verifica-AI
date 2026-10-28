import asyncio

import pytest

from threat_intel_sync.worker import WorkerSettings, run_forever


class CountingManager:
    def __init__(self, fail_on: set[int] | None = None) -> None:
        self.calls = 0
        self._fail_on = fail_on or set()

    async def sync_feeds(self) -> dict[str, int]:
        self.calls += 1
        if self.calls in self._fail_on:
            raise RuntimeError("feed down")
        return {"total_synced": 1, "sources": 1}


def stop_after(cycles: int):
    """Fake sleep that records the waits and stops the loop after N cycles."""
    waits: list[float] = []

    async def sleep(seconds: float) -> None:
        waits.append(seconds)
        if len(waits) >= cycles:
            raise asyncio.CancelledError

    return sleep, waits


async def test_worker_syncs_on_start_and_then_every_interval():
    manager = CountingManager()
    sleep, waits = stop_after(3)

    with pytest.raises(asyncio.CancelledError):
        await run_forever(manager, interval_seconds=1800, sleep=sleep)

    assert manager.calls == 3
    assert waits == [1800, 1800, 1800]


async def test_a_failed_cycle_does_not_stop_the_worker():
    manager = CountingManager(fail_on={1})
    sleep, _ = stop_after(2)

    with pytest.raises(asyncio.CancelledError):
        await run_forever(manager, interval_seconds=60, sleep=sleep)

    assert manager.calls == 2


def test_interval_comes_from_settings_in_minutes():
    assert WorkerSettings(SYNC_INTERVAL_MINUTES=15).interval_seconds == 900
