import json
from pathlib import Path

from research_runner.domain.dataset import Sample, parse_samples

DEFAULT_DATASET = Path(__file__).resolve().parents[2] / "data" / "benchmark_dataset.json"


def load_samples(path: Path | str | None = None) -> list[Sample]:
    with open(path or DEFAULT_DATASET, encoding="utf-8") as f:
        return parse_samples(json.load(f))
