"""Thesis tables (Markdown and LaTeX) built from the study report.

The text is in Portuguese for the monograph."""

from typing import Any

MODE_LABELS = {
    "heuristic": "Modo 1 (Heurístico / Feeds + Sinais de Domínio)",
    "classical_nlp": "Modo 1b (NLP Clássico / TF-IDF + LogReg)",
    "pure_vlm": "Modo 2 (VLM Puro Multimodal)",
    "cascade": "Modo 3 (Cascata Verifica AI)",
}

LATEX_MODE_LABELS = {
    "heuristic": "Modo 1 (Heur\\'istico / Sinais de Dom\\'inio)",
    "classical_nlp": "Modo 1b (NLP Cl\\'assico TF-IDF+LR)",
    "pure_vlm": "Modo 2 (VLM Puro Multimodal)",
    "cascade": "\\textbf{Modo 3 (Cascata Verifica AI)}",
}

NOT_EXECUTED = "não executado"


def generate_markdown_table(modes: list[dict[str, Any]]) -> str:
    lines = [
        "| Modo | Acurácia | Precisão | Recall | F1 | F2 | ECE | P95 (ms) | Custo / 1k (USD) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for mode in modes:
        label = MODE_LABELS.get(mode["mode"], mode["mode"])
        if mode["status"] != "executed":
            lines.append(f"| {label} | {NOT_EXECUTED}: {mode.get('note', '')} |" + " — |" * 7)
            continue
        m = mode["metrics"]
        lines.append(
            f"| {label} | {m['accuracy'] * 100:.1f}% | {m['precision']:.3f} | {m['recall']:.3f} | "
            f"{m['f1_score']:.3f} | {m['f2_score']:.3f} | {m['ece']:.3f} | "
            f"{m['p95_latency_ms']:.1f} | "
            f"${m['cost_per_1k_usd']:.3f} |"
        )
    return "\n".join(lines)


def generate_latex_table(modes: list[dict[str, Any]]) -> str:
    rows = [_latex_row(mode) for mode in modes]
    return "\n".join(
        [
            "\\begin{table}[htbp]",
            "\\centering",
            "\\caption{Resultados do Estudo de Ablação no conjunto de teste (amostras reais)}",
            "\\label{tab:ablation_results}",
            "\\begin{tabular}{lcccccccc}",
            "\\toprule",
            "\\textbf{Modo} & \\textbf{Acc.} & \\textbf{Prec.} & \\textbf{Rec.} & "
            "\\textbf{F1} & \\textbf{F2} & "
            "\\textbf{ECE} & \\textbf{P95 (ms)} & \\textbf{Custo/1k (USD)} \\\\",
            "\\midrule",
            *rows,
            "\\bottomrule",
            "\\end{tabular}",
            "\\end{table}",
        ]
    )


def _latex_row(mode: dict[str, Any]) -> str:
    label = LATEX_MODE_LABELS.get(mode["mode"], mode["mode"])
    if mode["status"] != "executed":
        return f"{label} & \\multicolumn{{8}}{{c}}{{{NOT_EXECUTED}}} \\\\"
    m = mode["metrics"]
    return (
        f"{label} & {m['accuracy'] * 100:.1f}\\% & {m['precision']:.3f} & {m['recall']:.3f} & "
        f"{m['f1_score']:.3f} & {m['f2_score']:.3f} & {m['ece']:.3f} & {m['p95_latency_ms']:.1f} & "
        f"\\${m['cost_per_1k_usd']:.3f} \\\\"
    )


# --- R9: uncertainty of each number, the answers that are not GOLPE, and false alarms. ---

UNCERTAINTY_COLUMNS = 6


def _percent_interval(ci: list[float], dash: str, pct: str) -> str:
    return f"{ci[0] * 100:.1f}{dash}{ci[1] * 100:.1f}{pct}"


def _ratio_interval(ci: list[float], dash: str) -> str:
    return f"{ci[0]:.3f}{dash}{ci[1]:.3f}"


def _false_alarm(false_alarm: dict[str, Any], pct: str) -> str:
    if not false_alarm["samples"]:
        return "sem amostras"
    golpe = false_alarm["golpe_rate"] * 100
    cuidado = false_alarm["cuidado_rate"] * 100
    return f"{golpe:.1f}{pct} / {cuidado:.1f}{pct} (n={false_alarm['samples']})"


def _uncertainty_cells(mode: dict[str, Any], dash: str, pct: str) -> list[str]:
    m = mode["metrics"]
    return [
        _percent_interval(m["accuracy_ci"], dash, pct),
        _ratio_interval(m["precision_ci"], dash),
        _ratio_interval(m["recall_ci"], dash),
        f"{m['caution_rate'] * 100:.1f}{pct}",
        f"{m['inconclusive_rate'] * 100:.1f}{pct}",
        _false_alarm(mode["false_alarm"], pct),
    ]


def generate_markdown_uncertainty_table(modes: list[dict[str, Any]]) -> str:
    lines = [
        "| Modo | Acurácia (IC 95%) | Precisão (IC 95%) | Recall (IC 95%) | CUIDADO | "
        "INCONCLUSIVO | Falso alarme: GOLPE / CUIDADO |",
        "|---|---|---|---|---|---|---|",
    ]
    for mode in modes:
        label = MODE_LABELS.get(mode["mode"], mode["mode"])
        if mode["status"] != "executed":
            skipped = f"| {label} | {NOT_EXECUTED}: {mode.get('note', '')} |"
            lines.append(skipped + " — |" * (UNCERTAINTY_COLUMNS - 1))
            continue
        lines.append(f"| {label} | " + " | ".join(_uncertainty_cells(mode, "–", "%")) + " |")
    return "\n".join(lines)


def generate_latex_uncertainty_table(modes: list[dict[str, Any]]) -> str:
    rows = []
    for mode in modes:
        label = LATEX_MODE_LABELS.get(mode["mode"], mode["mode"])
        if mode["status"] != "executed":
            columns = UNCERTAINTY_COLUMNS
            rows.append(f"{label} & \\multicolumn{{{columns}}}{{c}}{{{NOT_EXECUTED}}} \\\\")
            continue
        rows.append(f"{label} & " + " & ".join(_uncertainty_cells(mode, "--", "\\%")) + " \\\\")
    return "\n".join(
        [
            "\\begin{table}[htbp]",
            "\\centering",
            "\\caption{Intervalos de confiança de 95\\% (Wilson), respostas CUIDADO e "
            "INCONCLUSIVO e falso alarme em mensagens legítimas que parecem golpe}",
            "\\label{tab:ablation_uncertainty}",
            "\\begin{tabular}{lcccccc}",
            "\\toprule",
            "\\textbf{Modo} & \\textbf{Acc. (IC)} & \\textbf{Prec. (IC)} & \\textbf{Rec. (IC)} & "
            "\\textbf{CUIDADO} & \\textbf{INCONCL.} & \\textbf{Falso alarme} \\\\",
            "\\midrule",
            *rows,
            "\\bottomrule",
            "\\end{tabular}",
            "\\end{table}",
        ]
    )
