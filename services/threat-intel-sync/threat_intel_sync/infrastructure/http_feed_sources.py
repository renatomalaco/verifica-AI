import httpx

from threat_intel_sync.domain.feed_source import FeedSource, parse_url_lines, parse_urlhaus_content

OPENPHISH_FEED = "https://openphish.com/feed.txt"
# CaUMa (CERT.Bahia/RNP): manually verified scams aimed at people in Brazil, which the
# international lists mostly miss. It lists only URLs that are still online.
CAUMA_FEED = "https://cauma.pop-ba.rnp.br/feed/txt"
URLHAUS_FEED = "https://urlhaus.abuse.ch/downloads/csv_recent/"


async def _download(feed_url: str, client: httpx.AsyncClient | None) -> str:
    async with client or httpx.AsyncClient(timeout=15.0) as cli:
        resp = await cli.get(feed_url)
        resp.raise_for_status()
        return resp.text


class TextFeedSource:
    """A feed with one URL per line."""

    def __init__(self, feed_url: str, client: httpx.AsyncClient | None = None) -> None:
        self.feed_url = feed_url
        self._client = client

    async def fetch_urls(self) -> list[str]:
        return parse_url_lines(await _download(self.feed_url, self._client))


class URLhausSource:
    def __init__(
        self, feed_url: str = URLHAUS_FEED, client: httpx.AsyncClient | None = None
    ) -> None:
        self.feed_url = feed_url
        self._client = client

    async def fetch_urls(self) -> list[str]:
        return parse_urlhaus_content(await _download(self.feed_url, self._client))


def scam_feed_sources() -> list[FeedSource]:
    return [TextFeedSource(OPENPHISH_FEED), TextFeedSource(CAUMA_FEED), URLhausSource()]
