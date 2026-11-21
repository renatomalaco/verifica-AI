from contracts import Persuasion, TriageResult

from scan_orchestrator.application.confirm_triage import ConfirmingTriage
from scan_orchestrator.domain.decision import ThresholdPolicy

CLEAR_SCAM = TriageResult(is_phishing=0.99, persuasion=Persuasion.AFFECTIVE_COERCION)
WOULD_BE_SAFE = TriageResult(is_phishing=0.03)
DOUBT = TriageResult(is_phishing=0.60, persuasion=Persuasion.URGENCY)
DEEP = TriageResult(is_phishing=0.95, persuasion=Persuasion.FINANCIAL_THREAT)


class TwoModels:
    def __init__(self, quick: TriageResult | None, deep: TriageResult | None = DEEP) -> None:
        self._quick = quick
        self._deep = deep
        self.deep_calls = 0

    async def triage(self, text: str) -> TriageResult | None:
        return self._quick

    async def deep_triage(self, text: str) -> TriageResult | None:
        self.deep_calls += 1
        return self._deep


def _confirming(models: TwoModels) -> ConfirmingTriage:
    return ConfirmingTriage(models, ThresholdPolicy(scam=0.90, safe=0.10))


async def test_a_clear_scam_answers_without_the_deep_model():
    models = TwoModels(quick=CLEAR_SCAM)

    assert await _confirming(models).triage("oi pai, troquei de número") == CLEAR_SCAM
    assert models.deep_calls == 0


async def test_doubt_goes_to_the_deep_model():
    models = TwoModels(quick=DOUBT)

    assert await _confirming(models).triage("texto") == DEEP
    assert models.deep_calls == 1


async def test_a_would_be_safe_answer_is_confirmed_by_the_deep_model():
    models = TwoModels(quick=WOULD_BE_SAFE)

    assert await _confirming(models).triage("texto") == DEEP
    assert models.deep_calls == 1


async def test_without_confirmation_a_safe_answer_becomes_unknown():
    assert await _confirming(TwoModels(quick=WOULD_BE_SAFE, deep=None)).triage("texto") is None


async def test_when_the_quick_model_fails_the_deep_model_is_not_tried():
    models = TwoModels(quick=None)

    assert await _confirming(models).triage("texto") is None
    assert models.deep_calls == 0
