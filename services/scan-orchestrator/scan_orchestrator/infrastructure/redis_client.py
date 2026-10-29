import redis.asyncio as aioredis
from contracts import ScanResponse, normalize_url
from scan_orchestrator.domain.perceptual_hash import nearest, segments
from scan_orchestrator.domain.cascade import RedisCacheClientProtocol


class RedisCacheClient(RedisCacheClientProtocol):
    """Async client for Bloom filter, exact Set and verdict cache lookups in Redis."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0") -> None:
        self._redis_url = redis_url
        self._client: aioredis.Redis | None = None

    async def _get_client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = aioredis.from_url(self._redis_url, decode_responses=True)
        return self._client

    async def is_blacklisted(self, url: str) -> bool:
        norm_url = normalize_url(url)
        try:
            client = await self._get_client()
            # 1. Ultra-fast Bloom filter check (< 2ms)
            try:
                bloom_hit = await client.execute_command("BF.EXISTS", "blacklist:bloom", norm_url)
                if not bloom_hit:
                    return False
            except Exception:
                # If the Bloom filter module is not enabled, fall back to the exact Set
                pass

            # 2. Deterministic confirmation in the exact Set
            return bool(await client.sismember("blacklist:exact", norm_url))
        except Exception:
            return False

    async def get_cached_scan(self, sha256_hash: str) -> ScanResponse | None:
        try:
            client = await self._get_client()
            cached_raw = await client.get(f"scan:{sha256_hash}")
            if cached_raw:
                return ScanResponse.model_validate_json(cached_raw)
            return None
        except Exception:
            return None

    async def set_cached_scan(self, sha256_hash: str, response: ScanResponse, ttl: int = 3600) -> None:
        try:
            client = await self._get_client()
            await client.set(f"scan:{sha256_hash}", response.model_dump_json(), ex=ttl)
        except Exception:
            pass

    async def get_cached_phash(self, phash: str) -> ScanResponse | None:
        try:
            client = await self._get_client()
            candidates = await client.sunion(*[f"image:phash:seg:{seg}" for seg in segments(phash)])
            match = nearest(phash, set(candidates))
            cached_raw = await client.get(f"image:phash:{match}") if match else None
            return ScanResponse.model_validate_json(cached_raw) if cached_raw else None
        except Exception:
            return None

    async def set_cached_phash(self, phash: str, response: ScanResponse, ttl: int = 3600) -> None:
        try:
            client = await self._get_client()
            pipe = client.pipeline(transaction=True)
            pipe.set(f"image:phash:{phash}", response.model_dump_json(), ex=ttl)
            for seg in segments(phash):
                pipe.sadd(f"image:phash:seg:{seg}", phash)
                pipe.expire(f"image:phash:seg:{seg}", ttl)
            await pipe.execute()
        except Exception:
            pass

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
