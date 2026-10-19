from typing import Protocol

import httpx

from contracts import ExplainRequest, ExplainResult


class ExplainerClientProtocol(Protocol):
    async def explain(self, request: ExplainRequest) -> ExplainResult:
        ...


class FakeExplainerClient:
    def __init__(self, result: ExplainResult | None = None) -> None:
        self._result = result or ExplainResult(lines=["Test explanation."])
        self.requests: list[ExplainRequest] = []

    async def explain(self, request: ExplainRequest) -> ExplainResult:
        self.requests.append(request)
        return self._result


class FailingExplainerClient:
    async def explain(self, request: ExplainRequest) -> ExplainResult:
        raise RuntimeError("ai-gateway unavailable")


class HttpExplainerClient:
    """Asks the ai-gateway for the detailed (LLM) explanation of a persisted verdict."""

    def __init__(self, base_url: str, timeout_seconds: float = 12.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    async def explain(self, request: ExplainRequest) -> ExplainResult:
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    f"{self._base_url}/v1/explain",
                    json=request.model_dump(mode="json"),
                )
                response.raise_for_status()
                return ExplainResult.model_validate(response.json())
        except (httpx.HTTPError, ValueError) as exc:
            raise RuntimeError(f"Failed to request an explanation from the ai-gateway: {exc}") from exc
