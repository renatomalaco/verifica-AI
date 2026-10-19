import pytest
from research_runner.domain.ablation_models import AblationMode
from research_runner.application.benchmark_service import BenchmarkService, load_benchmark_dataset


def test_load_benchmark_dataset():
    samples = load_benchmark_dataset()
    assert len(samples) >= 20
    # Check that both GOLPE and SEGURO samples exist
    golpe_count = sum(1 for s in samples if s.expected_threat_level == "GOLPE")
    seguro_count = sum(1 for s in samples if s.expected_threat_level == "SEGURO")
    assert golpe_count > 5
    assert seguro_count > 5


def test_run_ablation_heuristic_mode():
    service = BenchmarkService()
    evaluation = service.run_mode(AblationMode.HEURISTIC)
    assert evaluation.mode == AblationMode.HEURISTIC
    assert len(evaluation.predictions) >= 20
    assert evaluation.metrics.cost_per_1k_usd == 0.0
    # Heuristic fails on text-only scams (cannot analyze raw text without URL)
    assert evaluation.metrics.recall < 0.90


def test_run_ablation_classical_nlp_mode():
    service = BenchmarkService()
    evaluation = service.run_mode(AblationMode.CLASSICAL_NLP)
    assert evaluation.mode == AblationMode.CLASSICAL_NLP
    assert len(evaluation.predictions) >= 20
    # Classical NLP performs well on known text phrases
    assert evaluation.metrics.f1_score >= 0.70


def test_run_ablation_cascade_mode():
    service = BenchmarkService()
    evaluation = service.run_mode(AblationMode.CASCADE)
    assert evaluation.mode == AblationMode.CASCADE
    assert len(evaluation.predictions) >= 20
    # Cascade Verifica AI achieves high F1 >= 0.92 with low operational cost
    assert evaluation.metrics.f1_score >= 0.92
    assert evaluation.metrics.cost_per_1k_usd < 0.50
    assert evaluation.metrics.p50_latency_ms < 100.0


def test_run_all_modes_comparative():
    service = BenchmarkService()
    evaluations = service.run_all_modes()
    assert len(evaluations) == 4
    modes = [e.mode for e in evaluations]
    assert AblationMode.HEURISTIC in modes
    assert AblationMode.CLASSICAL_NLP in modes
    assert AblationMode.PURE_VLM in modes
    assert AblationMode.CASCADE in modes

    # Cascade should have higher F1 than Heuristic
    cascade_eval = next(e for e in evaluations if e.mode == AblationMode.CASCADE)
    heuristic_eval = next(e for e in evaluations if e.mode == AblationMode.HEURISTIC)
    assert cascade_eval.metrics.f1_score > heuristic_eval.metrics.f1_score
