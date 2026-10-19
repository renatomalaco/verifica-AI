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
        scan = await self._repository.get(scan_id)
        if scan is None:
            raise ScanNotFoundError(str(scan_id))

        try:
            grant = await self._quota.consume(device_id, ip)
        except QuotaExceededError:
            raise
        except Exception as exc:
            raise ExplanationUnavailableError("Quota counter unavailable") from exc

        try:
            result = await self._explainer.explain(to_explain_request(scan, locale))
        except Exception as exc:
            await self._quota.refund(grant)
            raise ExplanationUnavailableError("Explanation unavailable") from exc

        return ExplainResponse(lines=result.lines, remaining_today=grant.remaining_today)


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
