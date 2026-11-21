import logging

import httpx
from contracts import TriageResult

logger = logging.getLogger(__name__)


class HttpTriageClient:
    """
    Async HTTP client that delegates content sanitization and classification
    to the ai-gateway microservice: a quick model, and a deep one that confirms.
    """

    def __init__(self, base_url: str = "http://localhost:8001", timeout_seconds: float = 2.0):
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    async def triage(self, text: str) -> TriageResult | None:
        return await self._post("/v1/triage", text)

    async def deep_triage(self, text: str) -> TriageResult | None:
        return await self._post("/v1/triage/deep", text)

    async def _post(self, path: str, text: str) -> TriageResult | None:
        # None sends the cascade to the ethical fallback (INCONCLUSIVO) instead of breaking the
        # analysis. The reason is logged, never the text: a silent None hid an overloaded model.
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(f"{self._base_url}{path}", json={"text": text})
        except httpx.HTTPError as exc:
            logger.warning("triage %s failed: %s", path, type(exc).__name__)
            return None
        if response.status_code != 200:
            logger.warning("triage %s answered %s", path, response.status_code)
            return None
        return TriageResult.model_validate(response.json())
