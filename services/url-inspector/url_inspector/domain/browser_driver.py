from typing import Protocol
from contracts import InspectResult


class BrowserDriverProtocol(Protocol):
    async def inspect(self, url: str, timeout_seconds: float = 6.0) -> InspectResult:
        ...
