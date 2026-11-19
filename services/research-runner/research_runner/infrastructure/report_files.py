"""Writes the study report (JSON) and one reliability diagram per executed mode, as SVG for the
web and PNG for the article (Word handles SVG badly)."""

import io
import json
import os
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")  # no display on the server
import matplotlib.pyplot as plt  # noqa: E402

DEFAULT_REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports"
SIZE = 320
PAD = 40
PNG_DPI = 200  # 800 px for a 4-inch figure: sharp at the article's column width
BAR = "#1F5464"
GUIDE = "#4E5E66"


def reports_dir() -> Path:
    return Path(os.environ.get("RESEARCH_REPORTS_DIR") or DEFAULT_REPORTS_DIR)


def write_report(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "latest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for mode in report["modes"]:
        if mode["status"] == "executed":
            name = f"reliability_{mode['mode']}"
            (out_dir / f"{name}.svg").write_text(render_reliability_svg(mode), encoding="utf-8")
            (out_dir / f"{name}.png").write_bytes(render_reliability_png(mode))


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
            f'<rect x="{x:.1f}" y="{SIZE - PAD - height:.1f}" '
            f'width="{width:.1f}" height="{height:.1f}" '
            f'fill="#1F5464"><title>{b["count"]} amostras, '
            f'acurácia {b["accuracy"]:.2f}</title></rect>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SIZE} {SIZE}" '
        'font-family="sans-serif" font-size="11">'
        f'<line x1="{PAD}" y1="{SIZE - PAD}" x2="{SIZE - PAD}" y2="{PAD}" '
        'stroke="#4E5E66" stroke-dasharray="4 4"/>'
        f"{''.join(bars)}"
        f'<line x1="{PAD}" y1="{SIZE - PAD}" x2="{SIZE - PAD}" y2="{SIZE - PAD}" stroke="#15232A"/>'
        f'<line x1="{PAD}" y1="{PAD}" x2="{PAD}" y2="{SIZE - PAD}" stroke="#15232A"/>'
        f'<text x="{SIZE / 2}" y="{SIZE - 8}" text-anchor="middle">Confiança</text>'
        f'<text x="12" y="{SIZE / 2}" text-anchor="middle" '
        f'transform="rotate(-90 12 {SIZE / 2})">Acurácia</text>'
        f'<text x="{SIZE / 2}" y="20" text-anchor="middle">'
        f'{mode["mode"]} — ECE {mode["metrics"]["ece"]:.3f}</text>'
        "</svg>"
    )


def render_reliability_png(mode: dict[str, Any]) -> bytes:
    """The same diagram as the SVG, for the article. matplotlib ships a font with accents."""
    figure, axes = plt.subplots(figsize=(4, 4), dpi=PNG_DPI)
    axes.plot([0, 1], [0, 1], linestyle="--", color=GUIDE, linewidth=1)
    for b in mode["reliability"]:
        width = b["upper"] - b["lower"]
        axes.bar(b["lower"], b["accuracy"], width=width * 0.95, align="edge", color=BAR)
    axes.set(xlim=(0, 1), ylim=(0, 1), xlabel="Confiança", ylabel="Acurácia")
    axes.set_title(f"{mode['mode']} — ECE {mode['metrics']['ece']:.3f}")
    figure.tight_layout()
    buffer = io.BytesIO()
    # No software version in the metadata, so the same report always gives the same bytes.
    figure.savefig(buffer, format="png", metadata={"Software": None})
    plt.close(figure)
    return buffer.getvalue()
