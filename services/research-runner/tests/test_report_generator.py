import pytest
from research_runner.domain.ablation_models import (
    AblationMode,
    ConfusionMatrix,
    MetricsReport,
    ModeEvaluation,
)
from research_runner.domain.report_generator import (
    generate_markdown_table,
    generate_latex_table,
    generate_full_tcc_report,
)


def _make_dummy_eval(mode: AblationMode, f1: float, cost: float) -> ModeEvaluation:
    report = MetricsReport(
        accuracy=f1,
        precision=f1,
        recall=f1,
        f1_score=f1,
        f2_score=f1,
        confusion_matrix=ConfusionMatrix(tp=10, fp=1, tn=9, fn=1),
        ece=0.05,
        p50_latency_ms=15.0,
        p95_latency_ms=45.0,
        p99_latency_ms=90.0,
        cost_per_1k_usd=cost,
        cost_per_1k_brl=cost * 5.50,
        total_samples=21,
        correct_samples=19,
    )
    return ModeEvaluation(mode=mode, metrics=report)


def test_markdown_table_generation():
    evals = [
        _make_dummy_eval(AblationMode.HEURISTIC, 0.72, 0.0),
        _make_dummy_eval(AblationMode.CLASSICAL_NLP, 0.81, 0.001),
        _make_dummy_eval(AblationMode.PURE_VLM, 0.89, 1.50),
        _make_dummy_eval(AblationMode.CASCADE, 0.95, 0.15),
    ]
    md = generate_markdown_table(evals)
    assert "| Modo |" in md
    assert "Acur" in md
    assert "Modo 1" in md
    assert "Modo 1b" in md
    assert "Modo 2" in md
    assert "Modo 3" in md
    assert "95.0%" in md or "0.95" in md


def test_latex_table_generation():
    evals = [
        _make_dummy_eval(AblationMode.HEURISTIC, 0.72, 0.0),
        _make_dummy_eval(AblationMode.CASCADE, 0.95, 0.15),
    ]
    tex = generate_latex_table(evals)
    assert "\\begin{table}" in tex
    assert "\\toprule" in tex
    assert "\\bottomrule" in tex
    assert "\\end{table}" in tex
    assert "Cascata Verifica AI" in tex


def test_full_tcc_report_generation():
    evals = [
        _make_dummy_eval(AblationMode.HEURISTIC, 0.72, 0.0),
        _make_dummy_eval(AblationMode.CASCADE, 0.95, 0.15),
    ]
    report = generate_full_tcc_report(evals)
    assert "# Relatório Científico de Ablação e Eficácia — Verifica AI" in report
    assert "Tabela Comparativa em Formato LaTeX" in report
    assert "Análise das Perguntas de Pesquisa" in report
