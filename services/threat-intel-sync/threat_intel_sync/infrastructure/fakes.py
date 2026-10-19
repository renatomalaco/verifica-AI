class FakeFeedSource:
    def __init__(self, urls: list[str]) -> None:
        self._urls = urls

    async def fetch_urls(self) -> list[str]:
        return list(self._urls)


class MemoryRedisStorage:
    """In-memory implementation for unit tests that simulates the Bloom Filter and exact Set."""

    def __init__(self) -> None:
        self._exact_set: set[str] = set()

    async def save_urls_atomically(self, urls: set[str]) -> None:
        self._exact_set = set(urls)

    def has_url(self, url: str) -> bool:
        return url in self._exact_set
