from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable
from uuid import uuid4

from scan_orchestrator.domain.quota import QuotaStore


@dataclass(frozen=True)
class ScanRateLimits:
    per_ip: int
    window_seconds: int


class ScanRateLimitedError(Exception):
    def __init__(self, retry_at: datetime) -> None:
        super().__init__(f"Too many scans until {retry_at.isoformat()}")
        self.retry_at = retry_at


class ScanRateLimit:
    """
    Per-IP sliding window on the public scan endpoints, against floods (each scan may pay
    for an LLM call and a browser). It is not a quota: the window is short and the person
    is told when to try again. Denied scans do not count, so retrying never extends the wait.
    """

    def __init__(
        self,
        store: QuotaStore,
        limits: ScanRateLimits,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._store = store
        self._limits = limits
        self._clock = clock

    async def check(self, ip: str) -> None:
        key, member = f"scan:ip:{ip}", uuid4().hex
        window = self._limits.window_seconds
        count, oldest = await self._store.window_add(key, member, self._clock().timestamp(), window)
        if count <= self._limits.per_ip:
            return
        await self._store.window_remove(key, member)
        raise ScanRateLimitedError(datetime.fromtimestamp(oldest + window, tz=timezone.utc))
