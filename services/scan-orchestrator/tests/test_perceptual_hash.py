import fakeredis.aioredis
import pytest

from contracts import Channel, ScanDetails, ScanResponse, ThreatLevel, VerdictMessage
from scan_orchestrator.domain.perceptual_hash import MAX_DISTANCE, hamming, segments
from scan_orchestrator.infrastructure.fakes import FakeRedisCacheClient
from scan_orchestrator.infrastructure.redis_client import RedisCacheClient

ORIGINAL = "c3d4e5f6a7b8c9d0"


def flip_bits(phash: str, positions: list[int]) -> str:
    value = int(phash, 16)
    for p in positions:
        value ^= 1 << p
    return f"{value:016x}"


def test_hamming_counts_differing_bits():
    assert hamming(ORIGINAL, ORIGINAL) == 0
    assert hamming(ORIGINAL, flip_bits(ORIGINAL, [0, 13, 40])) == 3


@pytest.mark.parametrize("positions", [[0, 1, 2, 3], [5, 18, 31, 44], [12, 25, 38, 51], [63, 62, 61, 60]])
def test_hashes_within_the_tolerance_always_share_a_segment(positions):
    # Pigeonhole: 4 flipped bits cannot touch all 5 segments, so at least one index matches.
    near = flip_bits(ORIGINAL, positions)
    assert set(segments(ORIGINAL)) & set(segments(near))
    assert MAX_DISTANCE == 4


def verdict() -> ScanResponse:
    return ScanResponse(
        id="00000000-0000-0000-0000-000000000001",
        threat_level=ThreatLevel.SCAM,
        verdict_message=VerdictMessage.SCAM_GENERIC,
        details=ScanDetails(channel=Channel.IMAGE, deciding_stage="image_ocr_triage"),
    )


@pytest.fixture(params=["fake", "redis"])
def cache(request):
    if request.param == "fake":
        return FakeRedisCacheClient()
    client = RedisCacheClient()
    client._client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    return client


async def test_recompressed_screenshot_hits_the_cache(cache):
    await cache.set_cached_phash(ORIGINAL, verdict())
    hit = await cache.get_cached_phash(flip_bits(ORIGINAL, [3, 17, 29, 50]))
    assert hit is not None and hit.threat_level is ThreatLevel.SCAM


async def test_a_different_image_misses_the_cache(cache):
    await cache.set_cached_phash(ORIGINAL, verdict())
    assert await cache.get_cached_phash(flip_bits(ORIGINAL, [1, 9, 17, 25, 33, 41])) is None
