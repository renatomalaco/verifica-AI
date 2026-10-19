import pytest

from scan_orchestrator.infrastructure.quota_store import RedisQuotaStore

# fakeredis is not yet in the root dev group; once installed, these tests run.
fakeredis = pytest.importorskip("fakeredis")


@pytest.fixture
def store():
    return RedisQuotaStore(client=fakeredis.FakeAsyncRedis(decode_responses=True))


async def test_increment_sets_ttl_only_on_first_hit(store):
    assert await store.increment("quota:d:20261016", 100) == 1
    assert await store.increment("quota:d:20261016", 100) == 2
    assert 0 < await store._get_client().ttl("quota:d:20261016") <= 100


async def test_decrement_never_goes_negative(store):
    await store.decrement("quota:d:202610")
    assert int(await store._get_client().get("quota:d:202610")) == 0


async def test_sliding_window_drops_old_entries(store):
    assert await store.window_add("quota:ip:x", "a", 1000.0, 60) == (1, 1000.0)
    assert await store.window_add("quota:ip:x", "b", 1030.0, 60) == (2, 1000.0)
    assert await store.window_add("quota:ip:x", "c", 1061.0, 60) == (2, 1030.0)
    await store.window_remove("quota:ip:x", "c")
    assert await store._get_client().zcard("quota:ip:x") == 1
