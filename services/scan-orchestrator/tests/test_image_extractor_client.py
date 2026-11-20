import httpx
import pytest

from scan_orchestrator.domain.cascade import ImageExtractionUnavailable
from scan_orchestrator.infrastructure.image_extractor_client import HttpImageExtractorClient


@pytest.mark.parametrize(
    "handler",
    [
        lambda request: (_ for _ in ()).throw(httpx.ReadTimeout("slow", request=request)),
        lambda request: httpx.Response(503),
    ],
)
async def test_a_slow_or_failing_reader_becomes_extraction_unavailable(handler):
    client = HttpImageExtractorClient(
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )

    with pytest.raises(ImageExtractionUnavailable):
        await client.extract("aW1n")
