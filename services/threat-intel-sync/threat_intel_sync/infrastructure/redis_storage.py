import redis.asyncio as aioredis
from threat_intel_sync.domain.sync_manager import RedisStorageProtocol


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
            return

        client = await self._get_client()
        temp_bloom = "blacklist:bloom:temp"
        temp_exact = "blacklist:exact:temp"

        # Clear leftover temporary structures, if any
        await client.delete(temp_bloom, temp_exact)

        # Create a temporary Bloom filter (false positive rate 0.001, capacity 5,000,000)
        try:
            await client.execute_command("BF.RESERVE", temp_bloom, "0.001", "5000000")
        except Exception:
            # In case the command is unsupported or the key already exists
            pass

        url_list = list(urls)
        batch_size = 1000
        for i in range(0, len(url_list), batch_size):
            batch = url_list[i : i + batch_size]
            pipe = client.pipeline()
            try:
                pipe.execute_command("BF.MADD", temp_bloom, *batch)
            except Exception:
                pass
            pipe.sadd(temp_exact, *batch)
            await pipe.execute()

        # Atomic swap in Redis
        try:
            await client.rename(temp_bloom, "blacklist:bloom")
        except Exception:
            pass
        await client.rename(temp_exact, "blacklist:exact")

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
