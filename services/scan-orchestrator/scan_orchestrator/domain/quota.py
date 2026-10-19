from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol
from uuid import uuid4

DAY_KEY_TTL_SECONDS = 2 * 24 * 3600
MONTH_KEY_TTL_SECONDS = 32 * 24 * 3600


class QuotaStore(Protocol):
    async def increment(self, key: str, ttl_seconds: int) -> int:
        ...

    async def decrement(self, key: str) -> None:
        ...

    async def window_add(self, key: str, member: str, now: float, window_seconds: int) -> tuple[int, float]:
        """Records `member` in the sliding window and returns (total in window, oldest instant)."""
        ...

    async def window_remove(self, key: str, member: str) -> None:
        ...


@dataclass(frozen=True)
class QuotaLimits:
    daily: int
    monthly: int
    ip_per_window: int
    ip_window_seconds: int


@dataclass(frozen=True)
class QuotaGrant:
    remaining_today: int
    day_key: str
    month_key: str
    ip_key: str
    ip_member: str


class QuotaExceededError(Exception):
    def __init__(self, retry_at: datetime) -> None:
        super().__init__(f"Quota exhausted until {retry_at.isoformat()}")
        self.retry_at = retry_at


class ExplainQuota:
    """
    Per-device "Me explica" quota (day and month in local time) with a per-IP cap over
    a sliding window. Only "Me explica" goes through here: the verdict and "o que fazer"
    are never limited. Denied attempts do not consume quota.
    """

    def __init__(
        self,
        store: QuotaStore,
        limits: QuotaLimits,
        utc_offset_hours: int = -3,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._store = store
        self._limits = limits
        self._tz = timezone(timedelta(hours=utc_offset_hours))
        self._clock = clock

    async def consume(self, device_id: str, ip: str) -> QuotaGrant:
        now = self._clock()
        local = now.astimezone(self._tz)
        grant = QuotaGrant(
            remaining_today=0,
            day_key=f"quota:{device_id}:{local:%Y%m%d}",
            month_key=f"quota:{device_id}:{local:%Y%m}",
            ip_key=f"quota:ip:{ip}",
            ip_member=uuid4().hex,
        )

        day_count = await self._store.increment(grant.day_key, DAY_KEY_TTL_SECONDS)
        month_count = await self._store.increment(grant.month_key, MONTH_KEY_TTL_SECONDS)
        ip_count, ip_oldest = await self._store.window_add(
            grant.ip_key, grant.ip_member, now.timestamp(), self._limits.ip_window_seconds
        )

        retry_at = self._retry_at(local, day_count, month_count, ip_count, ip_oldest)
        if retry_at is not None:
            await self.refund(grant)
            raise QuotaExceededError(retry_at)

        remaining = min(self._limits.daily - day_count, self._limits.monthly - month_count)
        return replace(grant, remaining_today=max(0, remaining))

    async def refund(self, grant: QuotaGrant) -> None:
        await self._store.decrement(grant.day_key)
        await self._store.decrement(grant.month_key)
        await self._store.window_remove(grant.ip_key, grant.ip_member)

    def _retry_at(
        self, local: datetime, day_count: int, month_count: int, ip_count: int, ip_oldest: float
    ) -> datetime | None:
        """When the quota resets: the latest among the exceeded limits (None if none was exceeded)."""
        candidates: list[datetime] = []
        if day_count > self._limits.daily:
            candidates.append(self._next_local_midnight(local))
        if month_count > self._limits.monthly:
            candidates.append(self._next_local_month(local))
        if ip_count > self._limits.ip_per_window:
            candidates.append(datetime.fromtimestamp(ip_oldest + self._limits.ip_window_seconds, tz=timezone.utc))
        return max(candidates, default=None)

    def _next_local_midnight(self, local: datetime) -> datetime:
        midnight = local.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        return midnight.astimezone(timezone.utc)

    def _next_local_month(self, local: datetime) -> datetime:
        year, month = (local.year + 1, 1) if local.month == 12 else (local.year, local.month + 1)
        return datetime(year, month, 1, tzinfo=self._tz).astimezone(timezone.utc)
