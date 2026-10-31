import json

import httpx
import pytest
import respx

from contracts import BrandMatchResult, ImageSource
from scan_orchestrator.domain.cascade import BrandMatchUnavailable
from scan_orchestrator.infrastructure.brand_matcher_client import HttpBrandMatcherClient

BASE = "http://ai-gateway.test"


async def test_sends_the_image_source_and_reads_the_result():
    async with respx.mock(base_url=BASE) as mock:
        route = mock.post("/v1/brand-match").respond(
            json=BrandMatchResult(matched_brand="Nubank", is_spoofing=True, similarity=0.9).model_dump()
        )
        result = await HttpBrandMatcherClient(BASE).match_brand("SHOT", "nubank-app.top", ImageSource.PAGE_SCREENSHOT)

    assert result.is_spoofing is True
    assert json.loads(route.calls.last.request.content)["image_source"] == "page_screenshot"


@pytest.mark.parametrize("reply", [{"status_code": 503}, {"status_code": 500}])
async def test_a_gateway_error_is_unavailable_not_a_clean_result(reply):
    # Returning an empty BrandMatchResult here used to read as "checked, no brand".
    async with respx.mock(base_url=BASE) as mock:
        mock.post("/v1/brand-match").respond(**reply)
        with pytest.raises(BrandMatchUnavailable):
            await HttpBrandMatcherClient(BASE).match_brand("SHOT", "x.top", ImageSource.PAGE_SCREENSHOT)


async def test_a_network_failure_is_unavailable():
    async with respx.mock(base_url=BASE) as mock:
        mock.post("/v1/brand-match").mock(side_effect=httpx.ConnectError("refused"))
        with pytest.raises(BrandMatchUnavailable):
            await HttpBrandMatcherClient(BASE).match_brand("SHOT", "x.top", ImageSource.USER_IMAGE)
