from typing import Protocol
import httpx
from contracts import ExtractRequest, ExtractResult


class ImageExtractorClientProtocol(Protocol):
    async def extract(self, image_b64: str) -> ExtractResult:
        ...


class FakeImageExtractorClient:
    def __init__(self, default_result: ExtractResult | None = None) -> None:
        self._default = default_result or ExtractResult(
            sha256="fake_sha256" * 4,
            phash="0000000000000000",
            extracted_text="",
            qr_codes=[],
            urls_found=[],
        )
        self.calls = 0

    def set_result(self, result: ExtractResult) -> None:
        self._default = result

    async def extract(self, image_b64: str) -> ExtractResult:
        self.calls += 1
        return self._default


class HttpImageExtractorClient(ImageExtractorClientProtocol):
    """HTTP client for the image-extractor microservice."""

    def __init__(
        self,
        base_url: str = "http://localhost:8003",
        timeout_seconds: float = 12.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._client = client

    async def extract(self, image_b64: str) -> ExtractResult:
        payload = ExtractRequest(image_b64=image_b64)
        if self._client:
            resp = await self._client.post(
                f"{self._base_url}/extract",
                json=payload.model_dump(),
                timeout=self._timeout_seconds,
            )
        else:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as cli:
                resp = await cli.post(
                    f"{self._base_url}/extract",
                    json=payload.model_dump(),
                )

        resp.raise_for_status()
        return ExtractResult.model_validate(resp.json())
