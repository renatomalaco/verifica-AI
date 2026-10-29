import redis.asyncio as aioredis
from threat_intel_sync.domain.sync_manager import RedisStorageProtocol


BATCH = 1000
TRANCO_KEY = "tranco:rank"  # read by the scan-orchestrator stage 1


class RedisStackStorage(RedisStorageProtocol):
    """Atomic Redis Stack storage with a Bloom Filter and an exact Set."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0") -> None:
        self._redis_url = redis_url
        self._client: aioredis.Redis | None = None

    async def _get_client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = aioredis.from_url(self._redis_url, decode_responses=True)
        return self._client

    async def save_urls_atomically(self, urls: set[str]) -> None:
        if not urls:
            return  # a feed that came back empty keeps the previous blacklist

        client = await self._get_client()
        temp_bloom, temp_exact = "blacklist:bloom:temp", "blacklist:exact:temp"
        await client.delete(temp_bloom, temp_exact)
        has_bloom = await self._reserve_bloom(client, temp_bloom)

        url_list = list(urls)
        for i in range(0, len(url_list), BATCH):
            batch = url_list[i : i + BATCH]
            pipe = client.pipeline(transaction=False)
            if has_bloom:
                pipe.execute_command("BF.MADD", temp_bloom, *batch)
            pipe.sadd(temp_exact, *batch)
            await pipe.execute()

        # Both renames in one MULTI/EXEC: readers never see a new Bloom with an old Set.
        swap = client.pipeline(transaction=True)
        if has_bloom:
            swap.rename(temp_bloom, "blacklist:bloom")
        swap.rename(temp_exact, "blacklist:exact")
        await swap.execute()

    async def save_tranco_ranks(self, ranks: dict[str, int]) -> None:
        if not ranks:
            return
        client = await self._get_client()
        temp = f"{TRANCO_KEY}:temp"
        await client.delete(temp)
        items = list(ranks.items())
        for i in range(0, len(items), BATCH):
            await client.hset(temp, mapping=dict(items[i : i + BATCH]))
        await client.rename(temp, TRANCO_KEY)

    @staticmethod
    async def _reserve_bloom(client: aioredis.Redis, key: str) -> bool:
        """Redis without the Bloom module still works with the exact Set alone."""
        try:
            await client.execute_command("BF.RESERVE", key, "0.001", "5000000")
            return True
        except aioredis.ResponseError:
            return False

    async def check_url(self, url: str) -> bool:
        client = await self._get_client()
        try:
            bloom_hit = await client.execute_command("BF.EXISTS", "blacklist:bloom", url)
            if not bloom_hit:
                return False
        except Exception:
            pass

        return bool(await client.sismember("blacklist:exact", url))

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
