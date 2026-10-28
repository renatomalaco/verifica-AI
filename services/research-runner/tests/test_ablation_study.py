import json

import pytest
from httpx import ASGITransport, AsyncClient

from research_runner.__main__ import main
from research_runner.application.ablation_study import StudyConfig, run_study
from research_runner.domain.dataset import Sample


def sample(id: str, content: str, label: str, origin: str = "real", channel: str = "texto") -> Sample:
    return Sample(id=id, channel=channel, content=content, label=label, origin=origin, source="t", collected_on="2026-10-01")


SCAMS = ["manda um pix urgente mae", "conta bloqueada regularize agora", "taxa da encomenda retida pague", "premio sorteio clique e resgate"]
SAFE = ["almoco de domingo na vovo", "consulta confirmada terca", "obrigado pela compra", "reuniao amanha as dez"]
REAL = [sample(f"g{i}", t, "GOLPE") for i, t in enumerate(SCAMS * 3)] + [sample(f"s{i}", t, "SEGURO") for i, t in enumerate(SAFE * 3)]
CONFIG = StudyConfig(test_ratio=0.25, seed=42)


async def test_study_evaluates_every_mode_on_the_test_split_only():
    report = await run_study(REAL, CONFIG)

    modes = {m["mode"]: m for m in report["modes"]}
    assert set(modes) == {"heuristic", "classical_nlp", "pure_vlm", "cascade"}
    assert report["meta"]["split"]["test"] == 6
    assert modes["cascade"]["metrics"]["total_samples"] == 6
    assert modes["pure_vlm"]["status"] == "not_executed"
    assert "metrics" not in modes["pure_vlm"]


async def test_report_declares_what_did_not_run_for_real():
    report = await run_study(REAL, CONFIG)
    meta = report["meta"]
    assert "stage_2_inspection" in meta["disabled_stages"]
    assert "local" in meta["triage"]
    assert meta["seed"] == 42
    assert len(meta["dataset_sha256"]) == 64


async def test_report_carries_reliability_bins_and_adversarial_results():
    report = await run_study(REAL, CONFIG)
    cascade = next(m for m in report["modes"] if m["mode"] == "cascade")
    assert all({"lower", "upper", "count", "accuracy", "mean_confidence"} <= set(b) for b in cascade["reliability"])
    assert set(report["adversarial"]) == {"total", "detected_without_sanitization", "detected_with_sanitization"}


async def test_without_real_samples_the_report_warns_instead_of_inventing_numbers():
    synthetic = [sample(f"x{i}", t, "GOLPE", origin="synthetic") for i, t in enumerate(SCAMS)]
    synthetic += [sample(f"y{i}", t, "SEGURO", origin="synthetic") for i, t in enumerate(SAFE)]
    report = await run_study(synthetic, CONFIG)
    assert report["meta"]["split"]["test"] == 0
    assert any("real" in w for w in report["meta"]["warnings"])


def write_dataset(tmp_path, samples):
    path = tmp_path / "dataset.json"
    items = [{**s.__dict__} for s in samples]
    path.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    return path


def test_gate_refuses_to_pass_without_a_test_split(tmp_path):
    synthetic = [sample(f"x{i}", t, "GOLPE", origin="synthetic") for i, t in enumerate(SCAMS)]
    synthetic += [sample(f"y{i}", t, "SEGURO", origin="synthetic") for i, t in enumerate(SAFE)]
    code = main(["--dataset", str(write_dataset(tmp_path, synthetic)), "--output-dir", str(tmp_path), "--threshold-f1", "0.5"])
    assert code == 2


def test_gate_compares_the_cascade_f1_on_the_test_split(tmp_path):
    dataset = write_dataset(tmp_path, REAL)
    assert main(["--dataset", str(dataset), "--output-dir", str(tmp_path), "--threshold-f1", "0.0"]) == 0
    assert main(["--dataset", str(dataset), "--output-dir", str(tmp_path), "--threshold-f1", "1.01"]) == 1
    assert json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))["modes"]
    assert (tmp_path / "reliability_cascade.svg").read_text(encoding="utf-8").startswith("<svg")


@pytest.fixture
def reports_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("RESEARCH_REPORTS_DIR", str(tmp_path))
    return tmp_path


async def test_api_serves_the_latest_report_or_404(reports_dir):
    from research_runner.api.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        missing = await client.get("/pesquisa/report")
        (reports_dir / "latest.json").write_text(json.dumps({"modes": [], "meta": {}}), encoding="utf-8")
        found = await client.get("/pesquisa/report")

    assert missing.status_code == 404
    assert found.status_code == 200
    assert found.json()["modes"] == []
    assert found.json()["latex_table"].startswith(r"\begin{table}")
