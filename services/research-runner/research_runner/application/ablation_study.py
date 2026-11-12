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
    PROVIDER_FAILURE,
    CascadeEvaluator,
    ClassicalNlpEvaluator,
    GatewayTriageClient,
    HeuristicEvaluator,
    LocalTriageClient,
    PureVlmEvaluator,
    train_classifier,
)
from research_runner.infrastructure.llm_providers import StudyProviders

DISABLED_STAGES = [
    # RDAP, crt.sh and Tranco need the network; the benchmark runs offline
    "stage_1_registry_lookups",
    "stage_2_inspection",
    "visual_rag",  # needs the R4 Visual RAG
]
LOCAL_TRIAGE = (
    "local classical classifier (TF-IDF + LogReg) trained on the train split; no LLM configured"
)
REAL_TRIAGE = (
    "ai-gateway triage path (PII masking + untrusted-content envelope) calling {provider} {model}"
)
# deciding_stage of a sample whose model call failed, per mode (the cascade answers INCONCLUSIVO).
FAILURE_STAGES = {
    AblationMode.PURE_VLM.value: PROVIDER_FAILURE,
    AblationMode.CASCADE.value: "contingency_fallback",
}


@dataclass(frozen=True)
class StudyConfig:
    test_ratio: float = 0.3
    seed: int = 42
    feed_urls: tuple[str, ...] = ()
    feed_snapshot: str | None = None  # where and when the feed URLs were taken


async def run_study(
    samples: list[Sample], config: StudyConfig, providers: StudyProviders = StudyProviders()
) -> dict[str, Any]:
    """Without providers no model is called: Mode 2 is not executed and the cascade triage
    stays local."""
    splits = assign_splits(samples, test_ratio=config.test_ratio, seed=config.seed)
    test = [s for s in samples if splits[s.id] is Split.TEST]
    classifier = train_classifier(samples, splits)
    feeds = list(config.feed_urls)
    triage = (
        GatewayTriageClient(providers.triage.call)
        if providers.triage
        else LocalTriageClient(classifier)
    )

    evaluators = {
        AblationMode.HEURISTIC: HeuristicEvaluator.with_feed(feeds),
        AblationMode.CLASSICAL_NLP: ClassicalNlpEvaluator(classifier),
        AblationMode.PURE_VLM: PureVlmEvaluator(providers.pure_vlm.call)
        if providers.pure_vlm
        else None,
        AblationMode.CASCADE: CascadeEvaluator.build(triage, feeds),
    }
    calls_model = {AblationMode.PURE_VLM: True, AblationMode.CASCADE: providers.triage is not None}
    evaluations = [
        await _evaluate(mode, evaluator, test, providers, calls_model.get(mode, False))
        for mode, evaluator in evaluators.items()
    ]
    adversarial = evaluate_adversarial(
        test, scam_probability=classifier.scam_probability, sanitize=sanitize_text
    )
    modes = [_mode_entry(e) for e in evaluations]

    return {
        "meta": _meta(samples, splits, test, config, providers, modes),
        "modes": modes,
        "adversarial": asdict(adversarial),
    }


async def _evaluate(
    mode: AblationMode, evaluator, test: list[Sample], providers: StudyProviders, calls_model: bool
) -> ModeEvaluation:
    if not test:
        return await run_mode(
            mode, None, test, not_executed_reason="no real samples in the test split"
        )
    pause = providers.pause_seconds if calls_model else 0.0
    # Only Mode 2 can lack an evaluator, so its reason is the only one ever shown.
    return await run_mode(
        mode, evaluator, test, not_executed_reason=providers.pure_vlm_missing, pause_seconds=pause
    )


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


def _meta(
    samples: list[Sample],
    splits: dict[str, Split],
    test: list[Sample],
    config: StudyConfig,
    providers: StudyProviders,
    modes: list[dict[str, Any]],
) -> dict[str, Any]:
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
        "triage": REAL_TRIAGE.format(**providers.triage.description)
        if providers.triage
        else LOCAL_TRIAGE,
        "llm": {
            "pure_vlm": providers.pure_vlm.description if providers.pure_vlm else None,
            "triage": providers.triage.description if providers.triage else None,
            "pause_seconds": providers.pause_seconds,
        },
        "disabled_stages": DISABLED_STAGES,
        "feed": {"urls": len(config.feed_urls), "snapshot": config.feed_snapshot},
        "warnings": _warnings(test, config, providers) + _failure_warnings(modes),
    }


def _warnings(test: list[Sample], config: StudyConfig, providers: StudyProviders) -> list[str]:
    warnings = []
    if not test:
        warnings.append(
            "test split is empty: collect real, anonymized samples before reporting any number"
        )
    if not config.feed_urls:
        warnings.append("no feed snapshot loaded: stage 0 cannot match any URL")
    if providers.pure_vlm and not providers.triage:
        warnings.append(
            "Mode 2 calls a real model but the cascade triage is the local classifier "
            f"({providers.triage_missing}): "
            "set AI_PROVIDER=gemini or jev before comparing them"
        )
    return warnings


def _failure_warnings(modes: list[dict[str, Any]]) -> list[str]:
    warnings = []
    for mode in modes:
        failed = mode.get("stage_breakdown", {}).get(FAILURE_STAGES.get(mode["mode"], ""), 0)
        if failed:
            warnings.append(
                f"{mode['mode']}: {failed} samples where the model call failed "
                "(timeout, rate limit or malformed "
                "answer), counted as INCONCLUSIVO"
            )
    return warnings


def _dataset_hash(samples: list[Sample]) -> str:
    canonical = json.dumps(
        [asdict(s) for s in sorted(samples, key=lambda s: s.id)], ensure_ascii=False, sort_keys=True
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
