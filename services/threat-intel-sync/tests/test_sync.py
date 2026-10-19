import pytest
from contracts import normalize_url
from threat_intel_sync.domain.feed_source import parse_urlhaus_content
from threat_intel_sync.domain.sync_manager import SyncManager
from threat_intel_sync.infrastructure.fakes import FakeFeedSource, MemoryRedisStorage


@pytest.mark.asyncio
async def test_parse_urlhaus_content():
    sample_csv = """# URLhaus Database dump
# Date: 2026-10-12
# https://urlhaus.abuse.ch/
"1","2026-10-12 10:00:00","https://phish-banco-falso.com/login","online","phishing"
"2","2026-10-12 10:05:00","http://promo-maliciosa.xyz/premio","online","malware"
# Fim
"""
    urls = parse_urlhaus_content(sample_csv)
    assert len(urls) == 2
    assert "https://phish-banco-falso.com/login" in urls
    assert "http://promo-maliciosa.xyz/premio" in urls


@pytest.mark.asyncio
async def test_sync_manager_aggregates_and_stores_atomically():
    source1 = FakeFeedSource([
        "https://phish1.com/login?utm_source=spam",
        "https://phish2.com/promo",
    ])
    source2 = FakeFeedSource([
        "https://phish2.com/promo",  # duplicada proposital
        "http://phish3.com/recadastro",
    ])

    storage = MemoryRedisStorage()
    manager = SyncManager(feed_sources=[source1, source2], storage=storage)

    result = await manager.sync_feeds()

    assert result["total_synced"] == 3  # phish1, phish2, phish3
    assert storage.has_url(normalize_url("https://phish1.com/login")) is True
    assert storage.has_url(normalize_url("https://phish2.com/promo")) is True
    assert storage.has_url(normalize_url("http://phish3.com/recadastro")) is True
    assert storage.has_url("https://site-legitimo.com.br") is False
