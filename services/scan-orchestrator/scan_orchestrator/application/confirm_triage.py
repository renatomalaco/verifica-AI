from typing import Protocol

from contracts import TriageResult

from scan_orchestrator.domain.decision import ThresholdPolicy, needs_confirmation, settle


class TwoDepthTriage(Protocol):
    async def triage(self, text: str) -> TriageResult | None: ...

    async def deep_triage(self, text: str) -> TriageResult | None: ...


class ConfirmingTriage:
    """A light model answers first; a stronger one confirms doubt and every would-be SEGURO.

    Clear scams (most of what people paste) stay fast and cheap, and SEGURO needs both models.
    """

    def __init__(self, models: TwoDepthTriage, policy: ThresholdPolicy) -> None:
        self._models = models
        self._policy = policy

    async def triage(self, text: str) -> TriageResult | None:
        quick = await self._models.triage(text)
        if quick is None or not needs_confirmation(quick, self._policy):
            return quick
        deep = await self._models.deep_triage(text)
        return settle(quick, deep, self._policy)
