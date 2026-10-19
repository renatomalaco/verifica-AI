import httpx
from contracts import BrandMatchRequest, BrandMatchResult
from scan_orchestrator.domain.cascade import BrandMatcherClientProtocol


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

    async def match_brand(self, image_b64: str, current_domain: str | None = None) -> BrandMatchResult:
        payload = BrandMatchRequest(image_b64=image_b64, current_domain=current_domain)
        try:
            if self._client:
                resp = await self._client.post(
                    f"{self._base_url}/v1/brand-match",
                    json=payload.model_dump(),
                    timeout=self._timeout_seconds,
                )
            else:
                async with httpx.AsyncClient(timeout=self._timeout_seconds) as cli:
                    resp = await cli.post(
                        f"{self._base_url}/v1/brand-match",
                        json=payload.model_dump(),
                    )

            if resp.status_code == 200:
                return BrandMatchResult.model_validate(resp.json())

            return BrandMatchResult()
        except Exception:
            return BrandMatchResult()
