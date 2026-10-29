"""Long-running worker: refreshes the scam URL feeds in Redis on a fixed interval."""

import asyncio
import logging
from collections.abc import Awaitable, Callable

from pydantic_settings import BaseSettings, SettingsConfigDict

from threat_intel_sync.domain.sync_manager import SyncManager
from threat_intel_sync.infrastructure.http_feed_sources import OpenPhishSource, URLhausSource
from threat_intel_sync.infrastructure.redis_storage import RedisStackStorage
from threat_intel_sync.infrastructure.tranco_source import TrancoSource

logger = logging.getLogger("threat_intel_sync.worker")


class WorkerSettings(BaseSettings):
    REDIS_URL: str = "redis://localhost:6379/0"
    SYNC_INTERVAL_MINUTES: int = 30
    TRANCO_INTERVAL_HOURS: int = 24  # the list changes slowly and the download is large
    TRANCO_TOP: int = 100_000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def interval_seconds(self) -> int:
        return self.SYNC_INTERVAL_MINUTES * 60

    @property
    def tranco_interval_seconds(self) -> int:
        return self.TRANCO_INTERVAL_HOURS * 3600


Job = Callable[[], Awaitable[dict[str, int]]]


async def run_forever(
    job: Job,
    interval_seconds: float,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> None:
    while True:
        await _run_once(job)
        await sleep(interval_seconds)


async def _run_once(job: Job) -> None:
    # A failed cycle keeps the previous data in Redis; the next cycle tries again.
    try:
        logger.info("sync done: %s", await job())
    except Exception:
        logger.exception("sync failed; retrying on the next cycle")


async def refresh_tranco(source, storage) -> dict[str, int]:
    ranks = await source.fetch_ranks()
    await storage.save_tranco_ranks(ranks)
    return {"tranco_domains": len(ranks)}


async def main() -> None:
    settings = WorkerSettings()
    storage = RedisStackStorage(redis_url=settings.REDIS_URL)
    manager = SyncManager(feed_sources=[OpenPhishSource(), URLhausSource()], storage=storage)
    tranco = TrancoSource(top=settings.TRANCO_TOP)
    try:
        await asyncio.gather(
            run_forever(manager.sync_feeds, settings.interval_seconds),
            run_forever(lambda: refresh_tranco(tranco, storage), settings.tranco_interval_seconds),
        )
    finally:
        await storage.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
