import argparse
import asyncio
import sys
from pathlib import Path

from research_runner.application.ablation_study import StudyConfig, run_study
from research_runner.domain.report_generator import (
    generate_latex_table,
    generate_latex_uncertainty_table,
    generate_markdown_table,
    generate_markdown_uncertainty_table,
)
from research_runner.infrastructure.dataset_file import load_samples
from research_runner.infrastructure.llm_providers import providers_from_settings
from research_runner.infrastructure.report_files import reports_dir, write_report
from research_runner.infrastructure.url_snapshots import load_url_snapshots
from research_runner.settings import ResearchSettings

GATE_PASSED = 0
GATE_FAILED = 1
NO_TEST_DATA = 2


def main(argv: list[str] | None = None) -> int:
    args = _parse(argv)
    feed_urls = _read_feed(args.feed_snapshot)
    url_snapshots, url_snapshots_sha = (
        load_url_snapshots(args.url_snapshots) if args.url_snapshots else (None, None)
    )
    config = StudyConfig(
        test_ratio=args.test_ratio,
        seed=args.seed,
        feed_urls=tuple(feed_urls),
        feed_snapshot=args.feed_snapshot,
        url_snapshots=url_snapshots,
        url_snapshots_path=args.url_snapshots,
        url_snapshots_sha256=url_snapshots_sha,
    )
    report = asyncio.run(
        run_study(load_samples(args.dataset), config, providers_from_settings(ResearchSettings()))
    )
    out_dir = Path(args.output_dir) if args.output_dir else reports_dir()
    write_report(report, out_dir)

    print(generate_markdown_table(report["modes"]))
    print()
    print(generate_latex_table(report["modes"]))
    print()
    print(generate_markdown_uncertainty_table(report["modes"]))
    print()
    print(generate_latex_uncertainty_table(report["modes"]))
    for warning in report["meta"]["warnings"]:
        print(f"[WARNING] {warning}")
    print(f"[OK] report written to {out_dir / 'latest.json'}")

    if args.threshold_f1 is None:
        return GATE_PASSED
    return _gate(report, args.threshold_f1, mode=args.gate_mode)


def _gate(report: dict, threshold: float, mode: str = "cascade") -> int:
    entry = next(m for m in report["modes"] if m["mode"] == mode)
    if entry["status"] != "executed":
        print(f"[FAIL] F1 gate ({mode}): not evaluated ({entry.get('note')})")
        return NO_TEST_DATA
    f1 = entry["metrics"]["f1_score"]
    passed = f1 >= threshold
    print(
        f"[{'OK' if passed else 'FAIL'}] F1 gate ({mode}) on the test split: {f1:.4f} "
        f"(threshold {threshold:.4f})"
    )
    return GATE_PASSED if passed else GATE_FAILED


def _read_feed(path: str | None) -> list[str]:
    if not path:
        return []
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def _parse(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verifica AI research runner: ablation study and F1 gate."
    )
    parser.add_argument(
        "--dataset",
        default=None,
        help="Benchmark dataset JSON (default: data/benchmark_dataset.json).",
    )
    parser.add_argument(
        "--output-dir", default=None, help="Where latest.json and the SVG diagrams go."
    )
    parser.add_argument(
        "--threshold-f1", type=float, default=None, help="Minimum F1 on the test split."
    )
    parser.add_argument(
        "--gate-mode",
        default="cascade",
        choices=("heuristic", "classical_nlp", "pure_vlm", "cascade"),
        help="Mode checked by --threshold-f1 (default: cascade).",
    )
    parser.add_argument("--seed", type=int, default=42, help="Seed of the fixed train/test split.")
    parser.add_argument(
        "--test-ratio", type=float, default=0.3, help="Share of real samples held out for testing."
    )
    parser.add_argument(
        "--feed-snapshot", default=None, help="Text file with one scam URL per line (stage 0 feed)."
    )
    parser.add_argument(
        "--url-snapshots",
        default=None,
        help="JSON file with frozen domain signals and page inspections for stages 1 and 2.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    # The thesis tables have accents; Windows pipes default to cp1252.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
