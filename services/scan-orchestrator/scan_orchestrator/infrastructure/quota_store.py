import redis.asyncio as aioredis

from scan_orchestrator.domain.quota import QuotaStore


class InMemoryQuotaStore(QuotaStore):
    """In-memory implementation for tests and development without Redis (ignores TTL)."""

    def __init__(self) -> None:
        self.counters: dict[str, int] = {}
        self.windows: dict[str, dict[str, float]] = {}

    async def increment(self, key: str, ttl_seconds: int) -> int:
        self.counters[key] = self.counters.get(key, 0) + 1
        return self.counters[key]

    async def decrement(self, key: str) -> None:
        if self.counters.get(key, 0) > 0:
            self.counters[key] -= 1

    async def window_add(self, key: str, member: str, now: float, window_seconds: int) -> tuple[int, float]:
        window = self.windows.setdefault(key, {})
        for old_member, ts in list(window.items()):
            if ts <= now - window_seconds:
                del window[old_member]
        window[member] = now
        return len(window), min(window.values())

    async def window_remove(self, key: str, member: str) -> None:
        self.windows.get(key, {}).pop(member, None)


class RedisQuotaStore(QuotaStore):
    """Counters `quota:{device}:{yyyymmdd}` / `quota:{device}:{yyyymm}` and a per-IP window in a sorted set."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0", client: aioredis.Redis | None = None) -> None:
        self._redis_url = redis_url
        self._client = client

    def _get_client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = aioredis.from_url(self._redis_url, decode_responses=True)
        return self._client

    async def increment(self, key: str, ttl_seconds: int) -> int:
        client = self._get_client()
        count = int(await client.incr(key))
        if count == 1:
            await client.expire(key, ttl_seconds)
        return count

    async def decrement(self, key: str) -> None:
        client = self._get_client()
        if int(await client.decr(key)) < 0:
            await client.set(key, 0, keepttl=True)

    async def window_add(self, key: str, member: str, now: float, window_seconds: int) -> tuple[int, float]:
        client = self._get_client()
        async with client.pipeline(transaction=True) as pipe:
            pipe.zremrangebyscore(key, 0, now - window_seconds)
            pipe.zadd(key, {member: now})
            pipe.zcard(key)
            pipe.zrange(key, 0, 0, withscores=True)
            pipe.expire(key, window_seconds)
            _, _, count, oldest, _ = await pipe.execute()
        oldest_ts = float(oldest[0][1]) if oldest else now
        return int(count), oldest_ts

    async def window_remove(self, key: str, member: str) -> None:
        await self._get_client().zrem(key, member)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
