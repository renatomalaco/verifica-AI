import httpx

from threat_intel_sync.domain.feed_source import parse_openphish_content, parse_urlhaus_content


async def _download(feed_url: str, client: httpx.AsyncClient | None) -> str:
    async with client or httpx.AsyncClient(timeout=15.0) as cli:
        resp = await cli.get(feed_url)
        resp.raise_for_status()
        return resp.text


class OpenPhishSource:
    def __init__(self, feed_url: str = "https://openphish.com/feed.txt", client: httpx.AsyncClient | None = None) -> None:
        self._feed_url = feed_url
        self._client = client

    async def fetch_urls(self) -> list[str]:
        return parse_openphish_content(await _download(self._feed_url, self._client))


class URLhausSource:
    def __init__(
        self,
        feed_url: str = "https://urlhaus.abuse.ch/downloads/csv_recent/",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._feed_url = feed_url
        self._client = client

    async def fetch_urls(self) -> list[str]:
        return parse_urlhaus_content(await _download(self._feed_url, self._client))
