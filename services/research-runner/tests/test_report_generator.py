from research_runner.domain.report_generator import generate_latex_table, generate_markdown_table

METRICS = {
    "accuracy": 0.9, "precision": 0.8, "recall": 0.75, "f1_score": 0.774, "f2_score": 0.76,
    "ece": 0.05, "p95_latency_ms": 12.3, "cost_per_1k_usd": 0.0,
}
MODES = [
    {"mode": "cascade", "status": "executed", "metrics": METRICS},
    {"mode": "pure_vlm", "status": "not_executed", "note": "no LLM provider configured"},
]


def test_markdown_table_shows_measured_numbers_and_skipped_modes():
    table = generate_markdown_table(MODES)
    assert "| Modo 3 (Cascata Verifica AI) | 90.0% | 0.800 | 0.750 | 0.774 |" in table
    assert "não executado: no LLM provider configured" in table


def test_latex_table_never_prints_numbers_for_a_skipped_mode():
    table = generate_latex_table(MODES)
    assert r"\multicolumn{8}{c}{não executado}" in table
    assert "0.774" in table
