import io
import zipfile

import fakeredis.aioredis
import httpx
import respx

from threat_intel_sync.domain.tranco import parse_tranco_csv
from threat_intel_sync.infrastructure.redis_storage import RedisStackStorage
from threat_intel_sync.infrastructure.tranco_source import TrancoSource

CSV = "1,google.com\n2,youtube.com\n3,facebook.com\n"


def test_parse_keeps_only_the_top_n_domains():
    assert parse_tranco_csv(CSV, top=2) == {"google.com": 1, "youtube.com": 2}


def test_parse_ignores_malformed_lines():
    assert parse_tranco_csv("1,google.com\nlixo\n,\n3,ok.com", top=10) == {"google.com": 1, "ok.com": 3}


async def test_source_downloads_and_unzips_the_list():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("top-1m.csv", CSV)
    async with respx.mock() as mock:
        mock.get("https://tranco-list.eu/top-1m.csv.zip").respond(content=buffer.getvalue())
        assert await TrancoSource(top=3).fetch_ranks() == {"google.com": 1, "youtube.com": 2, "facebook.com": 3}


def storage_with(redis) -> RedisStackStorage:
    storage = RedisStackStorage()
    storage._client = redis
    return storage


async def test_tranco_ranks_replace_the_previous_list():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    await redis.hset("tranco:rank", mapping={"antigo.com": 7})

    await storage_with(redis).save_tranco_ranks({"google.com": 1})

    assert await redis.hgetall("tranco:rank") == {"google.com": "1"}


async def test_feed_swap_replaces_old_urls_and_keeps_them_when_the_feed_is_empty():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    storage = storage_with(redis)

    await storage.save_urls_atomically({"https://velho.example/"})
    await storage.save_urls_atomically({"https://novo.example/"})
    assert await redis.smembers("blacklist:exact") == {"https://novo.example/"}

    # An empty download (feed down) must not wipe the blacklist.
    await storage.save_urls_atomically(set())
    assert await redis.smembers("blacklist:exact") == {"https://novo.example/"}
