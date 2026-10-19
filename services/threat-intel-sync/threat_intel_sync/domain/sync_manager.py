import asyncio
from typing import Protocol
from contracts import normalize_url
from threat_intel_sync.domain.feed_source import FeedSource


class RedisStorageProtocol(Protocol):
    async def save_urls_atomically(self, urls: set[str]) -> None:
        ...


def _normalize_all(raw_urls: list[str]) -> set[str]:
    normalized: set[str] = set()
    for raw_url in filter(str.strip, raw_urls):
        # Public feeds occasionally contain garbage; one bad URL must not break the sync.
        try:
            normalized.add(normalize_url(raw_url.strip()))
        except Exception:
            continue
    return normalized


class SyncManager:
    """Orchestrates the threat intelligence feed sync cycle."""

    def __init__(self, feed_sources: list[FeedSource], storage: RedisStorageProtocol) -> None:
        self._feed_sources = feed_sources
        self._storage = storage

    async def sync_feeds(self) -> dict[str, int]:
        results = await asyncio.gather(*(source.fetch_urls() for source in self._feed_sources), return_exceptions=True)

        normalized_urls: set[str] = set()
        for urls in results:
            if isinstance(urls, Exception):
                continue  # one feed being down does not block syncing the others
            normalized_urls |= _normalize_all(urls)

        await self._storage.save_urls_atomically(normalized_urls)
        return {"total_synced": len(normalized_urls), "sources": len(self._feed_sources)}
