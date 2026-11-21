import pytest
from contracts import Persuasion, TriageResult

from ai_gateway.application.triage_with_reserve import TriageWithReserve

ANSWER = TriageResult(is_phishing=0.99, persuasion=Persuasion.AFFECTIVE_COERCION)


class AnsweringModel:
    def __init__(self) -> None:
        self.calls = 0

    async def classify(self, envelope: str) -> TriageResult:
        self.calls += 1
        return ANSWER


class OverloadedModel:
    async def classify(self, envelope: str) -> TriageResult:
        raise RuntimeError("Gemini HTTP error: 503 Service Unavailable")


async def test_the_primary_model_answers_without_touching_the_reserve():
    reserve = AnsweringModel()

    result = await TriageWithReserve(AnsweringModel(), reserve).classify("envelope")

    assert result == ANSWER
    assert reserve.calls == 0


async def test_an_overloaded_primary_hands_the_text_to_the_reserve():
    result = await TriageWithReserve(OverloadedModel(), AnsweringModel()).classify("envelope")

    assert result == ANSWER


async def test_when_both_models_fail_the_failure_reaches_the_caller():
    with pytest.raises(RuntimeError):
        await TriageWithReserve(OverloadedModel(), OverloadedModel()).classify("envelope")
