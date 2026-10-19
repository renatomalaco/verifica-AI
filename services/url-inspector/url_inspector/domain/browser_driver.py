from typing import Protocol
from contracts import InspectResult


class BrowserDriverProtocol(Protocol):
    async def inspect(self, url: str, timeout_seconds: float = 6.0) -> InspectResult:
        ...


class FakeBrowserDriver:
    """In-memory implementation for fast, deterministic unit tests."""

    def __init__(self, default_result: InspectResult | None = None) -> None:
        self._results: dict[str, InspectResult] = {}
        self._default_result = default_result or InspectResult(
            dom_text="Conteúdo de teste da página",
            final_url="https://fake-page.com",
            has_password_field=False,
            is_blocked=False,
        )

    def set_result(self, url: str, result: InspectResult) -> None:
        self._results[url] = result

    async def inspect(self, url: str, timeout_seconds: float = 6.0) -> InspectResult:
        if url in self._results:
            return self._results[url]
        return self._default_result
