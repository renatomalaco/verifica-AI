import httpx
import pytest

from research_runner.domain.dataset import Sample
from research_runner.infrastructure.evaluators import (
    PROVIDER_FAILURE,
    CascadeEvaluator,
    GatewayTriageClient,
    PureVlmEvaluator,
)
from research_runner.infrastructure.llm_providers import providers_from_settings

WITH_CPF = "Seu CPF 123.456.789-00 foi bloqueado, pague a taxa urgente"
FAILURES = [
    {"side_effect": httpx.ReadTimeout("lento")},
    {"json": {"candidates": [{"content": {"parts": [{"text": "{\"is_phishing\": \"alta\"}"}]}}]}},
    {"text": "not json"},
    {"status_code": 429},
]


def sample(content: str, label: str = "GOLPE", channel: str = "texto") -> Sample:
    return Sample(
        id="q", channel=channel, content=content, label=label, origin="real", source="teste"
    )


@pytest.fixture
def gemini_call(make_settings, gemini_env):
    return providers_from_settings(make_settings(**gemini_env)).pure_vlm.call


async def test_pure_vlm_sends_only_masked_content_inside_the_envelope(gemini, gemini_call):
    gemini.answers(0.97)
    outcome = await PureVlmEvaluator(gemini_call).evaluate(sample(WITH_CPF))

    sent = gemini.sent_texts()[0]
    assert "123.456.789-00" not in sent
    assert "[CPF_MASCARADO]" in sent
    assert "<untrusted_inspection_data>" in sent
    assert outcome.predicted == "GOLPE"
    assert outcome.scam_probability == 0.97
    assert outcome.deciding_stage == "pure_vlm"
    assert outcome.cost_usd == pytest.approx(0.0013)


async def test_pure_vlm_below_one_half_is_safe(gemini, gemini_call):
    gemini.answers(0.2)
    outcome = await PureVlmEvaluator(gemini_call).evaluate(sample("almoco de domingo", "SEGURO"))
    assert outcome.predicted == "SEGURO"
    assert outcome.scam_probability == 0.2


@pytest.mark.parametrize("failure", FAILURES)
async def test_pure_vlm_failures_count_as_inconclusive_never_safe(gemini, gemini_call, failure):
    gemini.fails_with(**failure)
    outcome = await PureVlmEvaluator(gemini_call).evaluate(sample("almoco de domingo", "SEGURO"))
    assert outcome.predicted == "INCONCLUSIVO"
    assert outcome.deciding_stage == PROVIDER_FAILURE
    assert outcome.cost_usd == 0.0


async def test_cascade_triage_goes_through_the_gateway_path_and_meters_its_cost(
    gemini, gemini_call
):
    gemini.answers(0.97)
    evaluator = CascadeEvaluator.build(GatewayTriageClient(gemini_call), feed_urls=[])

    outcome = await evaluator.evaluate(sample(WITH_CPF))

    assert "[CPF_MASCARADO]" in gemini.sent_texts()[0]
    assert outcome.predicted == "GOLPE"
    assert outcome.deciding_stage == "triage"
    assert outcome.cost_usd == pytest.approx(0.0013)


async def test_a_link_decided_by_the_feed_never_pays_for_the_model(gemini, gemini_call):
    gemini.answers(0.1)
    evaluator = CascadeEvaluator.build(
        GatewayTriageClient(gemini_call), feed_urls=["https://golpe.example/pix"]
    )

    outcome = await evaluator.evaluate(sample("https://golpe.example/pix", channel="url"))

    assert outcome.predicted == "GOLPE"
    assert outcome.cost_usd == 0.0
    assert gemini.sent_texts() == []


@pytest.mark.parametrize("failure", FAILURES)
async def test_cascade_triage_failures_count_as_inconclusive_never_safe(
    gemini, gemini_call, failure
):
    gemini.fails_with(**failure)
    evaluator = CascadeEvaluator.build(GatewayTriageClient(gemini_call), feed_urls=[])

    outcome = await evaluator.evaluate(sample("almoco de domingo", "SEGURO"))

    assert outcome.predicted == "INCONCLUSIVO"
    assert outcome.deciding_stage == "contingency_fallback"
    assert outcome.cost_usd == 0.0


@pytest.mark.parametrize(
    "failure", [{"side_effect": httpx.ReadTimeout("lento")}, {"json": {"answers": {}}}]
)
async def test_cascade_with_jev_meters_the_price_per_call_and_fails_closed(
    make_settings, jev_env, jev, failure
):
    triage = GatewayTriageClient(providers_from_settings(make_settings(**jev_env)).triage.call)
    evaluator = CascadeEvaluator.build(triage, feed_urls=[])

    jev.answers(0.95)
    answered = await evaluator.evaluate(sample(WITH_CPF))
    jev.fails_with(**failure)
    failed = await evaluator.evaluate(sample(WITH_CPF))

    assert "[CPF_MASCARADO]" in jev.sent_texts()[0]
    assert (answered.predicted, answered.cost_usd) == ("GOLPE", pytest.approx(0.002))
    assert (failed.predicted, failed.cost_usd) == ("INCONCLUSIVO", 0.0)
