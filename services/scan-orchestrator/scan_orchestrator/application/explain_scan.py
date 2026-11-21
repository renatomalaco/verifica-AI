from uuid import UUID

from contracts import DEFAULT_LOCALE, ExplainRequest, ExplainResponse, Locale, ScanResponse
from scan_orchestrator.domain.quota import ExplainQuota, QuotaExceededError
from scan_orchestrator.infrastructure.explainer_client import ExplainerClientProtocol
from scan_orchestrator.infrastructure.scan_repository import ScanRepository


class ScanNotFoundError(Exception):
    pass


class ExplanationUnavailableError(Exception):
    pass


class ExplainScanUseCase:
    """
    "Me explica" (R5b): fetches the persisted verdict, charges the device quota and
    asks the ai-gateway for the explanation. Only the verdict goes to the LLM, never
    the raw content (LGPD). If the explanation fails, the quota is refunded.
    """

    def __init__(
        self,
        repository: ScanRepository,
        explainer: ExplainerClientProtocol,
        quota: ExplainQuota,
    ) -> None:
        self._repository = repository
        self._explainer = explainer
        self._quota = quota

    async def execute(
        self, scan_id: UUID, device_id: str, ip: str, locale: Locale = DEFAULT_LOCALE
    ) -> ExplainResponse:
        scan = await self._find(scan_id)

        try:
            grant = await self._quota.consume(device_id, ip)
        except QuotaExceededError:
            raise
        except Exception as exc:
            raise ExplanationUnavailableError("Quota counter unavailable") from exc

        try:
            lines = await self._explain(scan, locale)
        except ExplanationUnavailableError:
            await self._quota.refund(grant)
            raise

        return ExplainResponse(lines=lines, remaining_today=grant.remaining_today)

    async def execute_without_quota(
        self, scan_id: UUID, locale: Locale = DEFAULT_LOCALE
    ) -> ExplainResponse:
        """For accounts whose role turned on "Me explica" without limit."""
        scan = await self._find(scan_id)
        return ExplainResponse(lines=await self._explain(scan, locale))

    async def _find(self, scan_id: UUID) -> ScanResponse:
        scan = await self._repository.get(scan_id)
        if scan is None:
            raise ScanNotFoundError(str(scan_id))
        return scan

    async def _explain(self, scan: ScanResponse, locale: Locale) -> list[str]:
        try:
            result = await self._explainer.explain(to_explain_request(scan, locale))
        except Exception as exc:
            raise ExplanationUnavailableError("Explanation unavailable") from exc
        return result.lines


def to_explain_request(scan: ScanResponse, locale: Locale = DEFAULT_LOCALE) -> ExplainRequest:
    details = scan.details
    return ExplainRequest(
        threat_level=scan.threat_level,
        channel=details.channel,
        deciding_stage=details.deciding_stage,
        category=details.category,
        verdict_message=scan.verdict_message,
        locale=locale,
        scores=details.scores,
        domain_signals=details.domain_signals or {},
        links_not_inspected=details.links_not_inspected,
    )
