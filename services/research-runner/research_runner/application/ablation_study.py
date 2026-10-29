"""The ablation study: train on the train split, measure every mode on the real test split."""

import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from ai_gateway.domain.sanitizer import sanitize_text

from research_runner.application.benchmark_service import run_mode
from research_runner.domain.ablation_models import AblationMode, ModeEvaluation
from research_runner.domain.adversarial_eval import evaluate_adversarial
from research_runner.domain.dataset import Sample, Split, assign_splits
from research_runner.domain.metrics import reliability_bins
from research_runner.infrastructure.evaluators import (
    CascadeEvaluator,
    ClassicalNlpEvaluator,
    HeuristicEvaluator,
    train_classifier,
)

DISABLED_STAGES = [
    "stage_1_registry_lookups",  # RDAP, crt.sh and Tranco need the network; the benchmark runs offline
    "stage_2_inspection",
    "visual_rag",  # needs the R4 Visual RAG
]
TRIAGE = "local classical classifier (TF-IDF + LogReg) trained on the train split; no LLM configured"
NO_LLM = "no LLM provider configured (GEMINI_API_KEY); labels are never copied"


@dataclass(frozen=True)
class StudyConfig:
    test_ratio: float = 0.3
    seed: int = 42
    feed_urls: tuple[str, ...] = ()
    feed_snapshot: str | None = None  # where and when the feed URLs were taken


async def run_study(samples: list[Sample], config: StudyConfig) -> dict[str, Any]:
    splits = assign_splits(samples, test_ratio=config.test_ratio, seed=config.seed)
    test = [s for s in samples if splits[s.id] is Split.TEST]
    classifier = train_classifier(samples, splits)
    feeds = list(config.feed_urls)

    evaluators = {
        AblationMode.HEURISTIC: HeuristicEvaluator.with_feed(feeds),
        AblationMode.CLASSICAL_NLP: ClassicalNlpEvaluator(classifier),
        AblationMode.PURE_VLM: None,
        AblationMode.CASCADE: CascadeEvaluator.build(classifier, feeds),
    }
    evaluations = [await _evaluate(mode, evaluator, test) for mode, evaluator in evaluators.items()]
    adversarial = evaluate_adversarial(test, scam_probability=classifier.scam_probability, sanitize=sanitize_text)

    return {
        "meta": _meta(samples, splits, test, config),
        "modes": [_mode_entry(e) for e in evaluations],
        "adversarial": asdict(adversarial),
    }


async def _evaluate(mode: AblationMode, evaluator, test: list[Sample]) -> ModeEvaluation:
    if not test:
        return await run_mode(mode, None, test, not_executed_reason="no real samples in the test split")
    return await run_mode(mode, evaluator, test, not_executed_reason=NO_LLM)


def _mode_entry(evaluation: ModeEvaluation) -> dict[str, Any]:
    entry: dict[str, Any] = {"mode": evaluation.mode.value, "status": evaluation.status}
    if evaluation.status != "executed":
        return {**entry, "note": evaluation.note}
    return {
        **entry,
        "metrics": asdict(evaluation.metrics),
        "stage_breakdown": evaluation.stage_breakdown,
        "reliability": [asdict(b) for b in reliability_bins(evaluation.predictions)],
    }


def _meta(samples: list[Sample], splits: dict[str, Split], test: list[Sample], config: StudyConfig) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seed": config.seed,
        "test_ratio": config.test_ratio,
        "dataset_sha256": _dataset_hash(samples),
        "split": {
            "train": sum(1 for s in samples if splits[s.id] is Split.TRAIN),
            "test": len(test),
            "test_by_channel_and_label": dict(Counter(f"{s.channel}/{s.label}" for s in test)),
            "origin": dict(Counter(s.origin for s in samples)),
        },
        "triage": TRIAGE,
        "disabled_stages": DISABLED_STAGES,
        "feed": {"urls": len(config.feed_urls), "snapshot": config.feed_snapshot},
        "warnings": _warnings(test, config),
    }


def _warnings(test: list[Sample], config: StudyConfig) -> list[str]:
    warnings = []
    if not test:
        warnings.append("test split is empty: collect real, anonymized samples before reporting any number")
    if not config.feed_urls:
        warnings.append("no feed snapshot loaded: stage 0 cannot match any URL")
    return warnings


def _dataset_hash(samples: list[Sample]) -> str:
    canonical = json.dumps([asdict(s) for s in sorted(samples, key=lambda s: s.id)], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
