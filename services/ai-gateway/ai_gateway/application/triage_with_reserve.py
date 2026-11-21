import logging

from contracts import TriageResult

from ai_gateway.domain.triage import TriageClient

logger = logging.getLogger(__name__)


class TriageWithReserve:
    """The quick model answers; when it fails (overloaded, slow), a reserve model gets one try.

    Models of one family share capacity: on 2026-11-21 gemini-3.8-flash answered 503 for minutes
    while the Flash-Lite models answered in under 2 s.
    """

    def __init__(self, primary: TriageClient, reserve: TriageClient) -> None:
        self._primary = primary
        self._reserve = reserve

    async def classify(self, envelope: str) -> TriageResult:
        try:
            return await self._primary.classify(envelope)
        except RuntimeError as exc:
            logger.warning("primary triage model failed, trying the reserve: %s", exc)
        return await self._reserve.classify(envelope)
