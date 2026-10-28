import itertools

from research_runner.application.benchmark_service import Outcome, run_mode
from research_runner.domain.ablation_models import AblationMode
from research_runner.domain.dataset import Sample, Split
from research_runner.infrastructure.evaluators import (
    CascadeEvaluator,
    ClassicalNlpEvaluator,
    HeuristicEvaluator,
    train_classifier,
)


def sample(id: str, content: str, label: str = "GOLPE", channel: str = "texto") -> Sample:
    return Sample(id=id, channel=channel, content=content, label=label, origin="real", source="teste")


TRAIN = [
    sample("t1", "me manda um pix urgente agora mae troquei de numero"),
    sample("t2", "sua conta foi bloqueada regularize urgente no link"),
    sample("t3", "pague a taxa da encomenda retida hoje"),
    sample("t4", "o almoco de domingo vai ser na casa da vovo", "SEGURO"),
    sample("t5", "sua consulta esta confirmada para terca", "SEGURO"),
    sample("t6", "obrigado pela compra volte sempre", "SEGURO"),
]
TRAIN_SPLITS = {s.id: Split.TRAIN for s in TRAIN}


class FixedEvaluator:
    def __init__(self, outcome: Outcome):
        self.outcome = outcome

    async def evaluate(self, sample: Sample) -> Outcome:
        return self.outcome


def fake_clock(step_seconds: float):
    ticks = itertools.count()
    return lambda: next(ticks) * step_seconds


async def test_latency_is_measured_around_each_prediction():
    evaluator = FixedEvaluator(Outcome(predicted="GOLPE", scam_probability=0.9, deciding_stage="x"))
    result = await run_mode(AblationMode.CASCADE, evaluator, [sample("a", "oi")], clock=fake_clock(0.012))
    assert result.predictions[0].latency_ms == 12.0


async def test_confidence_is_the_probability_of_the_predicted_label():
    evaluator = FixedEvaluator(Outcome(predicted="SEGURO", scam_probability=0.2, deciding_stage="x"))
    result = await run_mode(AblationMode.CASCADE, evaluator, [sample("a", "oi")], clock=fake_clock(0.001))
    assert abs(result.predictions[0].confidence - 0.8) < 1e-9


async def test_a_mode_without_a_provider_is_reported_as_not_executed():
    # Never fall back to copying the expected label (the old Mode 2 did exactly that).
    result = await run_mode(AblationMode.PURE_VLM, None, [sample("a", "oi")], not_executed_reason="no LLM provider")
    assert result.status == "not_executed"
    assert result.note == "no LLM provider"
    assert result.predictions == []


def test_classifier_learns_only_from_the_train_split():
    held_out = sample("h1", "palavraexclusivadoteste aparece so aqui")
    splits = {**TRAIN_SPLITS, "h1": Split.TEST}
    classifier = train_classifier(TRAIN + [held_out], splits)
    assert "palavraexclusivadoteste" not in classifier.vectorizer.vocabulary_


async def test_classical_nlp_mode_predicts_from_text():
    evaluator = ClassicalNlpEvaluator(train_classifier(TRAIN, TRAIN_SPLITS))
    outcome = await evaluator.evaluate(sample("q", "manda um pix urgente mae"))
    assert outcome.predicted == "GOLPE"
    assert outcome.cost_usd == 0.0


async def test_heuristic_mode_has_no_signal_for_text_without_links():
    outcome = await HeuristicEvaluator.with_feed([]).evaluate(sample("q", "manda um pix urgente mae"))
    assert outcome.predicted == "SEGURO"
    assert outcome.deciding_stage == "no_url_no_signal"


async def test_heuristic_mode_flags_a_link_found_in_the_feed_snapshot():
    evaluator = HeuristicEvaluator.with_feed(["https://golpe.example/pix"])
    outcome = await evaluator.evaluate(sample("q", "https://golpe.example/pix", channel="url"))
    assert outcome.predicted == "GOLPE"


async def test_cascade_mode_runs_the_real_orchestrator_use_case():
    evaluator = CascadeEvaluator.build(train_classifier(TRAIN, TRAIN_SPLITS), feed_urls=["https://golpe.example/pix"])

    linked = await evaluator.evaluate(sample("q1", "Olha que legal https://golpe.example/pix", "GOLPE"))
    plain = await evaluator.evaluate(sample("q2", "manda um pix urgente mae troquei de numero"))

    assert linked.predicted == "GOLPE"
    assert linked.deciding_stage.startswith("embedded_url")
    assert 0.0 <= plain.scam_probability <= 1.0
    assert plain.deciding_stage == "triage"
