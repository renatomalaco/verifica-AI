"""Runs one ablation mode over a set of samples, measuring every prediction."""

import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from research_runner.domain.ablation_models import AblationMode, ModeEvaluation, SamplePrediction
from research_runner.domain.dataset import Sample
from research_runner.domain.metrics import calculate_metrics


@dataclass(frozen=True)
class Outcome:
    predicted: str
    scam_probability: float
    deciding_stage: str
    cost_usd: float = 0.0  # measured from real token usage; local models cost nothing


class Evaluator(Protocol):
    async def evaluate(self, sample: Sample) -> Outcome:
        ...


async def run_mode(
    mode: AblationMode,
    evaluator: Evaluator | None,
    samples: list[Sample],
    clock: Callable[[], float] = time.perf_counter,
    not_executed_reason: str = "",
) -> ModeEvaluation:
    if evaluator is None:
        return ModeEvaluation(mode=mode, metrics=calculate_metrics([]), status="not_executed", note=not_executed_reason)

    predictions = [await _predict(evaluator, sample, clock) for sample in samples]
    return ModeEvaluation(
        mode=mode,
        metrics=calculate_metrics(predictions),
        predictions=predictions,
        stage_breakdown=dict(Counter(p.deciding_stage for p in predictions)),
    )


async def _predict(evaluator: Evaluator, sample: Sample, clock: Callable[[], float]) -> SamplePrediction:
    started = clock()
    outcome = await evaluator.evaluate(sample)
    latency_ms = (clock() - started) * 1000.0
    return SamplePrediction(
        sample_id=sample.id,
        expected=sample.label,
        predicted=outcome.predicted,
        confidence=_confidence(outcome),
        latency_ms=round(latency_ms, 3),
        cost_usd=outcome.cost_usd,
        deciding_stage=outcome.deciding_stage,
    )


def _confidence(outcome: Outcome) -> float:
    # Calibration (ECE) needs the probability the model gave to the label it chose.
    if outcome.predicted == "GOLPE":
        return outcome.scam_probability
    return 1.0 - outcome.scam_probability
