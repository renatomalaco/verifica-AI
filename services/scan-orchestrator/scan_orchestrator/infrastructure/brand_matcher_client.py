import logging

import httpx
from contracts import BrandMatchRequest, BrandMatchResult, ImageSource
from scan_orchestrator.domain.cascade import BrandMatchUnavailable, BrandMatcherClientProtocol

logger = logging.getLogger(__name__)


class HttpBrandMatcherClient(BrandMatcherClientProtocol):
    """HTTP client for the Visual RAG module in the ai-gateway."""

    def __init__(
        self,
        base_url: str = "http://localhost:8001",
        timeout_seconds: float = 10.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._client = client

    async def match_brand(
        self, image_b64: str, current_domain: str | None, image_source: ImageSource
    ) -> BrandMatchResult:
        payload = BrandMatchRequest(image_b64=image_b64, current_domain=current_domain, image_source=image_source)
        try:
            resp = await self._post(payload.model_dump(mode="json"))
            resp.raise_for_status()
            return BrandMatchResult.model_validate(resp.json())
        except (httpx.HTTPError, ValueError) as exc:
            # An empty result here would read as "checked, no brand"; the caller must know it failed.
            logger.warning("visual RAG unavailable: %r", exc)
            raise BrandMatchUnavailable(str(exc)) from exc

    async def _post(self, body: dict) -> httpx.Response:
        url = f"{self._base_url}/v1/brand-match"
        if self._client:
            return await self._client.post(url, json=body, timeout=self._timeout_seconds)
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            return await client.post(url, json=body)
