from PIL import Image

from research_runner.infrastructure.report_files import write_report

MODE = {
    "mode": "cascade",
    "status": "executed",
    "metrics": {"ece": 0.05},
    "reliability": [
        {"lower": 0.8, "upper": 0.9, "count": 3, "accuracy": 1.0, "mean_confidence": 0.85},
        {"lower": 0.4, "upper": 0.5, "count": 2, "accuracy": 0.5, "mean_confidence": 0.45},
    ],
}
REPORT = {"meta": {}, "modes": [MODE, {"mode": "pure_vlm", "status": "not_executed"}]}


def test_every_executed_mode_gets_a_png_diagram_for_word(tmp_path):
    write_report(REPORT, tmp_path)

    with Image.open(tmp_path / "reliability_cascade.png") as image:
        assert image.format == "PNG"
        assert image.width >= 600 and image.height == image.width
    assert (tmp_path / "reliability_cascade.svg").exists()
    assert not (tmp_path / "reliability_pure_vlm.png").exists()


def test_the_png_is_the_same_for_the_same_report(tmp_path):
    write_report(REPORT, tmp_path / "a")
    write_report(REPORT, tmp_path / "b")

    first = (tmp_path / "a" / "reliability_cascade.png").read_bytes()
    assert first == (tmp_path / "b" / "reliability_cascade.png").read_bytes()
