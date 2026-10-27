"""Long-running worker: refreshes the scam URL feeds in Redis on a fixed interval."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Protocol

from pydantic_settings import BaseSettings, SettingsConfigDict

from threat_intel_sync.domain.sync_manager import SyncManager
from threat_intel_sync.infrastructure.http_feed_sources import OpenPhishSource, URLhausSource
from threat_intel_sync.infrastructure.redis_storage import RedisStackStorage

logger = logging.getLogger("threat_intel_sync.worker")


class WorkerSettings(BaseSettings):
    REDIS_URL: str = "redis://localhost:6379/0"
    SYNC_INTERVAL_MINUTES: int = 30

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def interval_seconds(self) -> int:
        return self.SYNC_INTERVAL_MINUTES * 60


class Syncable(Protocol):
    async def sync_feeds(self) -> dict[str, int]:
        ...


async def run_forever(
    manager: Syncable,
    interval_seconds: float,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> None:
    while True:
        await _sync_once(manager)
        await sleep(interval_seconds)


async def _sync_once(manager: Syncable) -> None:
    # A failed cycle keeps the previous feed in Redis; the next cycle tries again.
    try:
        result = await manager.sync_feeds()
        logger.info("feeds synced: %s", result)
    except Exception:
        logger.exception("feed sync failed; retrying on the next cycle")


async def main() -> None:
    settings = WorkerSettings()
    storage = RedisStackStorage(redis_url=settings.REDIS_URL)
    manager = SyncManager(feed_sources=[OpenPhishSource(), URLhausSource()], storage=storage)
    try:
        await run_forever(manager, settings.interval_seconds)
    finally:
        await storage.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
