import httpx
import respx

from threat_intel_sync.domain import feed_source
from threat_intel_sync.domain.feed_source import parse_openphish_content
from threat_intel_sync.infrastructure.http_feed_sources import OpenPhishSource, URLhausSource


def test_domain_feed_source_has_no_http_client():
    assert not hasattr(feed_source, "httpx")


def test_parse_openphish_content_skips_blank_and_comment_lines():
    text = "# OpenPhish\nhttps://golpe1.com/login\n\n  https://golpe2.com  \n"
    assert parse_openphish_content(text) == ["https://golpe1.com/login", "https://golpe2.com"]


@respx.mock
async def test_openphish_source_fetches_feed():
    respx.get("https://feed.test/openphish.txt").mock(
        return_value=httpx.Response(200, text="# cabeçalho\nhttps://golpe1.com/login\n")
    )
    urls = await OpenPhishSource(feed_url="https://feed.test/openphish.txt").fetch_urls()
    assert urls == ["https://golpe1.com/login"]


@respx.mock
async def test_urlhaus_source_fetches_and_parses_csv():
    csv_body = '# URLhaus\n"1","2026-10-12 10:00:00","https://golpe.com/pix","online","phishing"\n'
    respx.get("https://feed.test/urlhaus.csv").mock(return_value=httpx.Response(200, text=csv_body))
    urls = await URLhausSource(feed_url="https://feed.test/urlhaus.csv").fetch_urls()
    assert urls == ["https://golpe.com/pix"]
