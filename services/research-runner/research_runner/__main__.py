import argparse
import sys
from research_runner.application.benchmark_service import BenchmarkService
from research_runner.domain.ablation_models import AblationMode
from research_runner.domain.report_generator import (
    generate_markdown_table,
    generate_latex_table,
    generate_full_tcc_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verifica AI Research Runner — Executável de Ablação, Métricas Acadêmicas e Gate de F1."
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="all",
        choices=["heuristic", "classical_nlp", "pure_vlm", "cascade", "all"],
        help="Modo de ablação a ser executado ('all' para comparação completa).",
    )
    parser.add_argument(
        "--threshold-f1",
        type=float,
        default=None,
        help="Limiar mínimo de F1-Score para aprovação no Gate de CI/CD (ex: 0.92).",
    )
    parser.add_argument(
        "--output-md",
        type=str,
        default=None,
        help="Caminho para exportação do relatório completo em Markdown.",
    )
    parser.add_argument(
        "--output-tex",
        type=str,
        default=None,
        help="Caminho para exportação da tabela em LaTeX (booktabs).",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        help="Caminho customizado para o arquivo de dataset JSON de benchmark.",
    )

    args = parser.parse_args()
    service = BenchmarkService(dataset_path=args.dataset)

    if args.mode == "all":
        evaluations = service.run_all_modes()
        md_table = generate_markdown_table(evaluations)
        latex_table = generate_latex_table(evaluations)

        print("\n" + "=" * 80)
        print("RESULTADOS DO ESTUDO DE ABLAÇÃO COMPARATIVA — VERIFICA AI")
        print("=" * 80)
        print(md_table)
        print("\n" + "-" * 80)
        print("TABELA LATEX FORMATADA (BOOKTABS PARA O TCC):")
        print("-" * 80)
        print(latex_table)

        if args.output_md:
            with open(args.output_md, "w", encoding="utf-8") as f:
                f.write(generate_full_tcc_report(evaluations))
            print(f"\n[OK] Relatório Markdown salvo em: {args.output_md}")

        if args.output_tex:
            with open(args.output_tex, "w", encoding="utf-8") as f:
                f.write(latex_table)
            print(f"\n[OK] Tabela LaTeX salva em: {args.output_tex}")

        # If a threshold is given in 'all' mode, evaluate the cascade
        if args.threshold_f1 is not None:
            cascade_eval = next(e for e in evaluations if e.mode == AblationMode.CASCADE)
            f1 = cascade_eval.metrics.f1_score
            print("\n" + "=" * 80)
            print(f"AVALIAÇÃO DO GATE DE CI/CD (Cascata): F1 obtido = {f1:.4f} | Limiar = {args.threshold_f1:.4f}")
            if f1 >= args.threshold_f1:
                print("[OK] GATE CIENTIFICO: APROVADO.")
                print("=" * 80)
                return 0
            else:
                print("[FALHA] GATE CIENTIFICO: REPROVADO (F1 abaixo da tolerância mínima).")
                print("=" * 80)
                return 1

        return 0

    else:
        mode_enum = AblationMode(args.mode)
        evaluation = service.run_mode(mode_enum)
        m = evaluation.metrics
        print("\n" + "=" * 80)
        print(f"RESULTADOS — MODO: {args.mode.upper()}")
        print("=" * 80)
        print(f"Acurácia:       {m.accuracy * 100:.2f}%")
        print(f"Precisão:       {m.precision:.4f}")
        print(f"Recall:         {m.recall:.4f}")
        print(f"F1-Score:       {m.f1_score:.4f}")
        print(f"F2-Score:       {m.f2_score:.4f}")
        print(f"ECE:            {m.ece:.4f}")
        print(f"P95 Latência:   {m.p95_latency_ms:.1f} ms")
        print(f"Custo / 1k:     ${m.cost_per_1k_usd:.4f} USD (R$ {m.cost_per_1k_brl:.2f})")
        print("=" * 80)

        if args.threshold_f1 is not None:
            if m.f1_score >= args.threshold_f1:
                print(f"[OK] GATE CIENTIFICO: APROVADO (F1 {m.f1_score:.4f} >= {args.threshold_f1:.4f})")
                return 0
            else:
                print(f"[FALHA] GATE CIENTIFICO: REPROVADO (F1 {m.f1_score:.4f} < {args.threshold_f1:.4f})")
                return 1

        return 0


if __name__ == "__main__":
    sys.exit(main())
