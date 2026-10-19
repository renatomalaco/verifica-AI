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


def calculate_ece(predictions: List[SamplePrediction], n_bins: int = 10) -> float:
    if not predictions:
        return 0.0

    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    total = len(predictions)

    for i in range(n_bins):
        bin_lower = bins[i]
        bin_upper = bins[i + 1]

        in_bin = [
            p for p in predictions
            if (bin_lower <= p.confidence < bin_upper) or (i == n_bins - 1 and p.confidence == bin_upper)
        ]

        if not in_bin:
            continue

        bin_size = len(in_bin)
        bin_accuracy = sum(1 for p in in_bin if p.is_correct) / bin_size
        bin_confidence = sum(p.confidence for p in in_bin) / bin_size

        ece += (bin_size / total) * abs(bin_accuracy - bin_confidence)

    return float(ece)


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
