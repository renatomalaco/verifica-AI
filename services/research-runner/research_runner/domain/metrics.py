from dataclasses import dataclass
from typing import List, Tuple
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
        members = [p for p in predictions if lower <= p.confidence < upper or (is_last and p.confidence == upper)]
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
    return float(sum(b.count / total * abs(b.accuracy - b.mean_confidence) for b in reliability_bins(predictions, n_bins)))


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
    )
