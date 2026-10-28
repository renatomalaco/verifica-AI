"""Writes the study report (JSON) and one reliability diagram (SVG) per executed mode."""

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports"
SIZE = 320
PAD = 40


def reports_dir() -> Path:
    return Path(os.environ.get("RESEARCH_REPORTS_DIR") or DEFAULT_REPORTS_DIR)


def write_report(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "latest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for mode in report["modes"]:
        if mode["status"] == "executed":
            (out_dir / f"reliability_{mode['mode']}.svg").write_text(render_reliability_svg(mode), encoding="utf-8")


def read_report(out_dir: Path) -> dict[str, Any] | None:
    path = out_dir / "latest.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def render_reliability_svg(mode: dict[str, Any]) -> str:
    """Bars = accuracy per confidence bin; the diagonal is perfect calibration."""
    plot = SIZE - 2 * PAD
    bars = []
    for b in mode["reliability"]:
        x = PAD + b["lower"] * plot
        width = (b["upper"] - b["lower"]) * plot - 2
        height = b["accuracy"] * plot
        bars.append(
            f'<rect x="{x:.1f}" y="{SIZE - PAD - height:.1f}" width="{width:.1f}" height="{height:.1f}" '
            f'fill="#1F5464"><title>{b["count"]} amostras, acurácia {b["accuracy"]:.2f}</title></rect>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SIZE} {SIZE}" font-family="sans-serif" font-size="11">'
        f'<line x1="{PAD}" y1="{SIZE - PAD}" x2="{SIZE - PAD}" y2="{PAD}" stroke="#4E5E66" stroke-dasharray="4 4"/>'
        f'{"".join(bars)}'
        f'<line x1="{PAD}" y1="{SIZE - PAD}" x2="{SIZE - PAD}" y2="{SIZE - PAD}" stroke="#15232A"/>'
        f'<line x1="{PAD}" y1="{PAD}" x2="{PAD}" y2="{SIZE - PAD}" stroke="#15232A"/>'
        f'<text x="{SIZE / 2}" y="{SIZE - 8}" text-anchor="middle">Confiança</text>'
        f'<text x="12" y="{SIZE / 2}" text-anchor="middle" transform="rotate(-90 12 {SIZE / 2})">Acurácia</text>'
        f'<text x="{SIZE / 2}" y="20" text-anchor="middle">{mode["mode"]} — ECE {mode["metrics"]["ece"]:.3f}</text>'
        "</svg>"
    )
