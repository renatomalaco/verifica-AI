"""Benchmark dataset rules: provenance and a fixed, stratified train/test split."""

import hashlib
from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal

Origin = Literal["real", "synthetic"]
REQUIRED_FIELDS = ("id", "channel", "content", "label", "origin", "source")
LABELS = {"GOLPE", "SEGURO"}
ORIGINS = {"real", "synthetic"}


class Split(StrEnum):
    TRAIN = "train"
    TEST = "test"


@dataclass(frozen=True)
class Sample:
    id: str
    channel: str
    content: str
    label: str
    origin: Origin
    source: str
    collected_on: str | None = None
    adversarial: bool = False
    category: str | None = None


def parse_samples(items: list[dict[str, Any]]) -> list[Sample]:
    samples = [_parse_one(item) for item in items]
    ids = [s.id for s in samples]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise ValueError(f"duplicate sample ids: {duplicates}")
    return samples


def _parse_one(item: dict[str, Any]) -> Sample:
    missing = [f for f in REQUIRED_FIELDS if not item.get(f)]
    if missing:
        raise ValueError(f"sample {item.get('id', '?')} is missing {missing} (origin and source are mandatory)")
    if item["label"] not in LABELS or item["origin"] not in ORIGINS:
        raise ValueError(f"sample {item['id']} has an invalid label or origin")
    known = {k: item[k] for k in Sample.__dataclass_fields__ if k in item}
    return Sample(**known)


def assign_splits(samples: list[Sample], test_ratio: float, seed: int) -> dict[str, Split]:
    """
    Only real samples can be tested. Within each (channel, label) stratum, samples are
    ordered by a seeded hash of their id, so the split does not depend on file order and
    adding one sample moves at most one other.
    """
    splits = {s.id: Split.TRAIN for s in samples}
    strata: dict[tuple[str, str], list[Sample]] = defaultdict(list)
    for s in samples:
        if s.origin == "real":
            strata[(s.channel, s.label)].append(s)

    for members in strata.values():
        ranked = sorted(members, key=lambda s: _rank(s.id, seed))
        for s in ranked[: round(len(ranked) * test_ratio)]:
            splits[s.id] = Split.TEST
    return splits


def _rank(sample_id: str, seed: int) -> str:
    return hashlib.sha256(f"{seed}:{sample_id}".encode("utf-8")).hexdigest()
