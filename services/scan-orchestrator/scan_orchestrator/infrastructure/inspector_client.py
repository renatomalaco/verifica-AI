import httpx
from contracts import InspectRequest, InspectResult
from scan_orchestrator.domain.cascade import InspectorClientProtocol


class HttpInspectorClient(InspectorClientProtocol):
    """HTTP client for the url-inspector microservice."""

    def __init__(
        self,
        base_url: str = "http://localhost:8002",
        timeout_seconds: float = 12.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._client = client

    async def inspect(self, url: str) -> InspectResult:
        payload = InspectRequest(url=url, timeout_seconds=self._timeout_seconds - 2.0)
        try:
            if self._client:
                resp = await self._client.post(
                    f"{self._base_url}/inspect",
                    json=payload.model_dump(),
                    timeout=self._timeout_seconds,
                )
            else:
                async with httpx.AsyncClient(timeout=self._timeout_seconds) as cli:
                    resp = await cli.post(
                        f"{self._base_url}/inspect",
                        json=payload.model_dump(),
                    )

            if resp.status_code == 200:
                return InspectResult.model_validate(resp.json())

            return InspectResult(
                final_url=url,
                is_blocked=True,
                blocked_reason=f"http_status_{resp.status_code}: {resp.text[:200]}",
            )
        except Exception as exc:
            return InspectResult(
                final_url=url,
                is_blocked=True,
                blocked_reason=f"network_failure: {type(exc).__name__}",
            )
