from research_runner.domain.report_generator import (
    generate_latex_table,
    generate_latex_uncertainty_table,
    generate_markdown_table,
    generate_markdown_uncertainty_table,
)

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


UNCERTAIN = {
    **METRICS,
    "accuracy_ci": [0.49, 0.94],
    "precision_ci": [0.6, 0.9],
    "recall_ci": [0.5, 0.88],
    "caution_rate": 0.1,
    "inconclusive_rate": 0.05,
}
UNCERTAIN_MODES = [
    {
        "mode": "cascade",
        "status": "executed",
        "metrics": UNCERTAIN,
        "false_alarm": {"samples": 4, "golpe_rate": 0.25, "cuidado_rate": 0.5},
    },
    {
        "mode": "heuristic",
        "status": "executed",
        "metrics": UNCERTAIN,
        "false_alarm": {"samples": 0, "golpe_rate": None, "cuidado_rate": None},
    },
    {"mode": "pure_vlm", "status": "not_executed", "note": "no LLM provider configured"},
]


def test_uncertainty_table_shows_intervals_rates_and_false_alarms():
    table = generate_markdown_uncertainty_table(UNCERTAIN_MODES)

    assert "| Modo 3 (Cascata Verifica AI) | 49.0–94.0% | 0.600–0.900 | 0.500–0.880 |" in table
    assert "| 10.0% | 5.0% | 25.0% / 50.0% (n=4) |" in table
    assert "sem amostras" in table
    assert "não executado" in table


def test_latex_uncertainty_table_escapes_percent_signs():
    table = generate_latex_uncertainty_table(UNCERTAIN_MODES)

    assert r"49.0--94.0\%" in table
    assert r"25.0\% / 50.0\% (n=4)" in table


def test_latex_uncertainty_table_is_valid_latex_text():
    table = generate_latex_uncertainty_table(UNCERTAIN_MODES)

    assert table.startswith(r"\begin{table}")
    assert r"\toprule" in table and r"\bottomrule" in table
    assert not any(ord(c) < 32 and c != "\n" for c in table)  # no \b or \t from a lost backslash
