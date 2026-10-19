import pytest
from research_runner.domain.ablation_models import SamplePrediction
from research_runner.domain.metrics import (
    calculate_confusion_matrix,
    calculate_metrics,
    calculate_ece,
    calculate_percentiles,
    calculate_cost_per_1k,
)


def test_confusion_matrix_calculation():
    predictions = [
        # TP: expected GOLPE, predicted GOLPE
        SamplePrediction("1", "GOLPE", "GOLPE", 0.95, 10.0, 0.001, "stage_1"),
        SamplePrediction("2", "GOLPE", "GOLPE", 0.90, 15.0, 0.001, "stage_1"),
        # TN: expected SEGURO, predicted SEGURO
        SamplePrediction("3", "SEGURO", "SEGURO", 0.98, 5.0, 0.000, "stage_0"),
        # FP: expected SEGURO, predicted GOLPE
        SamplePrediction("4", "SEGURO", "GOLPE", 0.85, 20.0, 0.002, "stage_2"),
        # FN: expected GOLPE, predicted SEGURO
        SamplePrediction("5", "GOLPE", "SEGURO", 0.60, 25.0, 0.002, "stage_2"),
    ]

    cm = calculate_confusion_matrix(predictions)
    assert cm.tp == 2
    assert cm.tn == 1
    assert cm.fp == 1
    assert cm.fn == 1


def test_calculate_metrics_values():
    predictions = [
        SamplePrediction("1", "GOLPE", "GOLPE", 0.95, 10.0, 0.001, "stage_1"),
        SamplePrediction("2", "GOLPE", "GOLPE", 0.90, 15.0, 0.001, "stage_1"),
        SamplePrediction("3", "SEGURO", "SEGURO", 0.98, 5.0, 0.000, "stage_0"),
        SamplePrediction("4", "SEGURO", "GOLPE", 0.85, 20.0, 0.002, "stage_2"),
        SamplePrediction("5", "GOLPE", "SEGURO", 0.60, 25.0, 0.002, "stage_2"),
    ]

    report = calculate_metrics(predictions)
    # Total = 5, Correct = 3 (acc = 0.60)
    assert report.total_samples == 5
    assert report.correct_samples == 3
    assert report.accuracy == pytest.approx(0.60, rel=1e-2)

    # Precision = TP / (TP + FP) = 2 / 3 = 0.6667
    assert report.precision == pytest.approx(0.6667, rel=1e-2)

    # Recall = TP / (TP + FN) = 2 / 3 = 0.6667
    assert report.recall == pytest.approx(0.6667, rel=1e-2)

    # F1 = 2 * (P * R) / (P + R) = 0.6667
    assert report.f1_score == pytest.approx(0.6667, rel=1e-2)

    # F2 = 5 * P * R / (4*P + R) = 0.6667
    assert report.f2_score == pytest.approx(0.6667, rel=1e-2)


def test_ece_calculation():
    # Perfectly calibrated predictions:
    # 5 items with 0.9 confidence where 90% (e.g. all or 4/5) are correct
    predictions = [
        SamplePrediction("1", "GOLPE", "GOLPE", 0.90, 10.0, 0.0, "s"),
        SamplePrediction("2", "GOLPE", "GOLPE", 0.90, 10.0, 0.0, "s"),
        SamplePrediction("3", "GOLPE", "GOLPE", 0.90, 10.0, 0.0, "s"),
        SamplePrediction("4", "GOLPE", "GOLPE", 0.90, 10.0, 0.0, "s"),
        SamplePrediction("5", "GOLPE", "SEGURO", 0.90, 10.0, 0.0, "s"),  # 4/5 = 0.80 accuracy, conf = 0.90 -> error 0.10
    ]
    ece = calculate_ece(predictions, n_bins=5)
    assert 0.0 <= ece <= 1.0
    assert ece == pytest.approx(0.10, rel=1e-2)


def test_percentile_latencies():
    latencies = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    p50, p95, p99 = calculate_percentiles(latencies)
    assert p50 <= p95 <= p99
    assert p50 == pytest.approx(55.0, rel=1e-1)


def test_cost_calculation():
    predictions = [
        SamplePrediction("1", "GOLPE", "GOLPE", 0.95, 10.0, 0.0001, "stage_1"),
        SamplePrediction("2", "GOLPE", "GOLPE", 0.95, 10.0, 0.0002, "stage_1"),
    ]
    cost_usd_1k, cost_brl_1k = calculate_cost_per_1k(predictions, usd_to_brl=5.50)
    # avg cost per req = 0.00015 -> per 1k = 0.15 USD -> * 5.50 = 0.825 BRL
    assert cost_usd_1k == pytest.approx(0.15, rel=1e-2)
    assert cost_brl_1k == pytest.approx(0.825, rel=1e-2)
