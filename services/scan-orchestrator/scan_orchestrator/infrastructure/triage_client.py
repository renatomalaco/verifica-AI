import httpx
from contracts import TriageResult


class HttpTriageClient:
    """
    Async HTTP client that delegates content sanitization and classification
    to the ai-gateway microservice.
    """

    def __init__(self, base_url: str = "http://localhost:8001", timeout_seconds: float = 2.0):
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    async def triage(self, text: str) -> TriageResult | None:
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    f"{self._base_url}/v1/triage",
                    json={"text": text},
                )
                if response.status_code == 200:
                    return TriageResult.model_validate(response.json())
                return None
        except httpx.HTTPError:
            # None sends the cascade to the ethical fallback (INCONCLUSIVO) instead of breaking the analysis.
            return None
