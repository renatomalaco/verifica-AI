import httpx
import respx

from threat_intel_sync.domain import feed_source
from threat_intel_sync.domain.feed_source import parse_url_lines
from threat_intel_sync.infrastructure.http_feed_sources import (
    TextFeedSource,
    URLhausSource,
    scam_feed_sources,
)


def test_domain_feed_source_has_no_http_client():
    assert not hasattr(feed_source, "httpx")


def test_parse_url_lines_skips_blank_and_comment_lines():
    text = "# OpenPhish\nhttps://golpe1.com/login\n\n  https://golpe2.com  \n"
    assert parse_url_lines(text) == ["https://golpe1.com/login", "https://golpe2.com"]


@respx.mock
async def test_text_feed_source_fetches_one_url_per_line():
    respx.get("https://feed.test/feed.txt").mock(
        return_value=httpx.Response(200, text="# cabeçalho\nhttps://golpe1.com/login\n")
    )
    urls = await TextFeedSource(feed_url="https://feed.test/feed.txt").fetch_urls()
    assert urls == ["https://golpe1.com/login"]


def test_scam_feeds_include_the_brazilian_cauma_catalog():
    # International lists miss most scams aimed at Brazil; CaUMa (CERT.Bahia/RNP) covers them.
    feed_urls = {source.feed_url for source in scam_feed_sources()}
    assert "https://cauma.pop-ba.rnp.br/feed/txt" in feed_urls
    assert "https://openphish.com/feed.txt" in feed_urls


@respx.mock
async def test_urlhaus_source_fetches_and_parses_csv():
    csv_body = '# URLhaus\n"1","2026-10-12 10:00:00","https://golpe.com/pix","online","phishing"\n'
    respx.get("https://feed.test/urlhaus.csv").mock(return_value=httpx.Response(200, text=csv_body))
    urls = await URLhausSource(feed_url="https://feed.test/urlhaus.csv").fetch_urls()
    assert urls == ["https://golpe.com/pix"]
