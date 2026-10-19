from typing import List
from research_runner.domain.ablation_models import AblationMode, ModeEvaluation


MODE_LABELS = {
    AblationMode.HEURISTIC: "Modo 1 (Heurístico / Feeds + Sinais de Domínio)",
    AblationMode.CLASSICAL_NLP: "Modo 1b (NLP Clássico / TF-IDF + LogReg)",
    AblationMode.PURE_VLM: "Modo 2 (VLM Puro Multimodal)",
    AblationMode.CASCADE: "Modo 3 (Cascata Verifica AI com Early Return)",
}

LATEX_MODE_LABELS = {
    AblationMode.HEURISTIC: "Modo 1 (Heur\\'istico / Sinais de Dom\\'inio)",
    AblationMode.CLASSICAL_NLP: "Modo 1b (NLP Cl\\'assico TF-IDF+LR)",
    AblationMode.PURE_VLM: "Modo 2 (VLM Puro Multimodal)",
    AblationMode.CASCADE: "\\textbf{Modo 3 (Cascata Verifica AI)}",
}


def generate_markdown_table(evaluations: List[ModeEvaluation]) -> str:
    lines = [
        "| Modo | Acurácia | Precisão | Recall | F1-Score | F2-Score | ECE | P95 (ms) | Custo / 1k (USD) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for ev in evaluations:
        m = ev.metrics
        label = MODE_LABELS.get(ev.mode, str(ev.mode))
        lines.append(
            f"| {label} | {m.accuracy * 100:.1f}% | {m.precision:.3f} | {m.recall:.3f} | "
            f"{m.f1_score:.3f} | {m.f2_score:.3f} | {m.ece:.3f} | {m.p95_latency_ms:.1f} | "
            f"${m.cost_per_1k_usd:.3f} |"
        )
    return "\n".join(lines)


def generate_latex_table(evaluations: List[ModeEvaluation]) -> str:
    latex_lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Resultados do Estudo de Ablação e Comparativo de Eficácia da Plataforma Verifica AI}",
        "\\label{tab:ablation_results}",
        "\\begin{tabular}{lcccccccc}",
        "\\toprule",
        "\\textbf{Modo} & \\textbf{Acc.} & \\textbf{Prec.} & \\textbf{Rec.} & \\textbf{F1} & \\textbf{F2} & \\textbf{ECE} & \\textbf{P95 (ms)} & \\textbf{Custo/1k (USD)} \\\\",
        "\\midrule",
    ]
    for ev in evaluations:
        m = ev.metrics
        label = LATEX_MODE_LABELS.get(ev.mode, str(ev.mode))
        latex_lines.append(
            f"{label} & {m.accuracy * 100:.1f}\\% & {m.precision:.3f} & {m.recall:.3f} & "
            f"{m.f1_score:.3f} & {m.f2_score:.3f} & {m.ece:.3f} & {m.p95_latency_ms:.1f} & "
            f"\\${m.cost_per_1k_usd:.3f} \\\\"
        )
    latex_lines.extend([
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table}",
    ])
    return "\n".join(latex_lines)


def generate_full_tcc_report(evaluations: List[ModeEvaluation]) -> str:
    md_table = generate_markdown_table(evaluations)
    latex_table = generate_latex_table(evaluations)

    return f"""# Relatório Científico de Ablação e Eficácia — Verifica AI

Documento gerado automaticamente pelo **research-runner** para embasamento experimental da defesa de TCC.

---

## 1. Tabela Comparativa de Ablação

{md_table}

---

## 2. Tabela Comparativa em Formato LaTeX (Booktabs)

```latex
{latex_table}
```

---

## 3. Análise das Perguntas de Pesquisa

- **Q1 (Necessidade de IA Multimodal):** A cascata equilibra o custo de processamento com short-circuit determinístico, acionando o VLM somente no resíduo não resolvido por heurísticas locais.
- **Q2 (Viabilidade de NLP Clássico):** O Modo 1b (TF-IDF + Regressão Logística) demonstra bom desempenho para frases conhecidas em PT-BR, mas carece de generalização para coerção afetiva contextual sem palavras-chave explícitas.
- **Q3 (Comparativo com Ferramentas de Domínio - SiteConfiável):** O Modo 1 (heurístico puro) falha em analisar textos sem URLs e imagens/prints de mensagens, cenários onde o Verifica AI alcança detecção robusta.
"""
