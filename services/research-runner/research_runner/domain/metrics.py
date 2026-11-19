from dataclasses import dataclass
import math
from typing import Any, List, Tuple
import numpy as np
from research_runner.domain.ablation_models import (
    ConfusionMatrix,
    MetricsReport,
    SamplePrediction,
)


def calculate_confusion_matrix(predictions: List[SamplePrediction]) -> ConfusionMatrix:
    tp = 0
    fp = 0
    tn = 0
    fn = 0

    for pred in predictions:
        is_expected_golpe = (pred.expected == "GOLPE")
        is_pred_golpe = (pred.predicted == "GOLPE")

        if is_expected_golpe and is_pred_golpe:
            tp += 1
        elif is_expected_golpe and not is_pred_golpe:
            fn += 1
        elif not is_expected_golpe and is_pred_golpe:
            fp += 1
        else:
            tn += 1

    return ConfusionMatrix(tp=tp, fp=fp, tn=tn, fn=fn)


@dataclass(frozen=True)
class ReliabilityBin:
    lower: float
    upper: float
    count: int
    accuracy: float
    mean_confidence: float


def reliability_bins(predictions: List[SamplePrediction], n_bins: int = 10) -> List[ReliabilityBin]:
    """Confidence buckets for the reliability diagram; empty buckets are left out."""
    edges = [round(float(e), 10) for e in np.linspace(0.0, 1.0, n_bins + 1)]
    bins: List[ReliabilityBin] = []
    for i, (lower, upper) in enumerate(zip(edges, edges[1:])):
        is_last = i == n_bins - 1
        members = [
            p
            for p in predictions
            if lower <= p.confidence < upper or (is_last and p.confidence == upper)
        ]
        if not members:
            continue
        accuracy = sum(1 for p in members if p.is_correct) / len(members)
        confidence = sum(p.confidence for p in members) / len(members)
        bins.append(ReliabilityBin(lower, upper, len(members), accuracy, confidence))
    return bins


def calculate_ece(predictions: List[SamplePrediction], n_bins: int = 10) -> float:
    if not predictions:
        return 0.0
    total = len(predictions)
    return float(
        sum(
            b.count / total * abs(b.accuracy - b.mean_confidence)
            for b in reliability_bins(predictions, n_bins)
        )
    )


def calculate_percentiles(latencies: List[float]) -> Tuple[float, float, float]:
    if not latencies:
        return 0.0, 0.0, 0.0
    arr = np.array(latencies)
    p50 = float(np.percentile(arr, 50))
    p95 = float(np.percentile(arr, 95))
    p99 = float(np.percentile(arr, 99))
    return p50, p95, p99


def calculate_cost_per_1k(
    predictions: List[SamplePrediction], usd_to_brl: float = 5.50
) -> Tuple[float, float]:
    if not predictions:
        return 0.0, 0.0
    avg_cost = sum(p.cost_usd for p in predictions) / len(predictions)
    cost_usd_1k = avg_cost * 1000.0
    cost_brl_1k = cost_usd_1k * usd_to_brl
    return float(cost_usd_1k), float(cost_brl_1k)


Z_95 = 1.959964


def wilson_interval(successes: int, total: int, z: float = Z_95) -> Tuple[float, float]:
    """Wilson score interval: unlike p ± z·se it stays in [0, 1] and works with few samples."""
    if total == 0:
        return 0.0, 1.0
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


def _rate(predictions: List[SamplePrediction], level: str) -> float:
    return sum(1 for p in predictions if p.predicted == level) / len(predictions)


def misclassified(predictions: List[SamplePrediction]) -> List[dict[str, str]]:
    """Wrong answers for the error analysis: ids and labels only, never the message."""
    return [
        {
            "id": p.sample_id,
            "expected": p.expected,
            "predicted": p.predicted,
            "deciding_stage": p.deciding_stage,
        }
        for p in predictions
        if not p.is_correct
    ]


def false_alarm_rates(predictions: List[SamplePrediction], group: set[str]) -> dict[str, Any]:
    """How often legitimate messages that look like scams were flagged."""
    members = [p for p in predictions if p.sample_id in group]
    if not members:
        return {"samples": 0, "golpe_rate": None, "cuidado_rate": None}
    return {
        "samples": len(members),
        "golpe_rate": _rate(members, "GOLPE"),
        "cuidado_rate": _rate(members, "CUIDADO"),
    }


def calculate_metrics(
    predictions: List[SamplePrediction], usd_to_brl: float = 5.50
) -> MetricsReport:
    total = len(predictions)
    if total == 0:
        return MetricsReport(
            accuracy=0.0,
            precision=0.0,
            recall=0.0,
            f1_score=0.0,
            f2_score=0.0,
            confusion_matrix=ConfusionMatrix(),
            ece=0.0,
            p50_latency_ms=0.0,
            p95_latency_ms=0.0,
            p99_latency_ms=0.0,
            cost_per_1k_usd=0.0,
            cost_per_1k_brl=0.0,
            total_samples=0,
            correct_samples=0,
        )

    cm = calculate_confusion_matrix(predictions)
    correct = sum(1 for p in predictions if p.is_correct)
    accuracy = correct / total

    precision = cm.tp / (cm.tp + cm.fp) if (cm.tp + cm.fp) > 0 else 0.0
    recall = cm.tp / (cm.tp + cm.fn) if (cm.tp + cm.fn) > 0 else 0.0

    if (precision + recall) > 0:
        f1_score = 2.0 * (precision * recall) / (precision + recall)
        f2_score = 5.0 * (precision * recall) / (4.0 * precision + recall)
    else:
        f1_score = 0.0
        f2_score = 0.0

    ece = calculate_ece(predictions)
    latencies = [p.latency_ms for p in predictions]
    p50, p95, p99 = calculate_percentiles(latencies)
    cost_usd_1k, cost_brl_1k = calculate_cost_per_1k(predictions, usd_to_brl=usd_to_brl)

    return MetricsReport(
        accuracy=accuracy,
        precision=precision,
        recall=recall,
        f1_score=f1_score,
        f2_score=f2_score,
        confusion_matrix=cm,
        ece=ece,
        p50_latency_ms=p50,
        p95_latency_ms=p95,
        p99_latency_ms=p99,
        cost_per_1k_usd=cost_usd_1k,
        cost_per_1k_brl=cost_brl_1k,
        total_samples=total,
        correct_samples=correct,
        accuracy_ci=wilson_interval(correct, total),
        precision_ci=wilson_interval(cm.tp, cm.tp + cm.fp),
        recall_ci=wilson_interval(cm.tp, cm.tp + cm.fn),
        caution_rate=_rate(predictions, "CUIDADO"),
        inconclusive_rate=_rate(predictions, "INCONCLUSIVO"),
    )
