import json

import pytest

from research_runner.domain.dataset import Sample, Split, assign_splits
from research_runner.infrastructure.dataset_file import load_samples


def sample(id: str, label: str = "GOLPE", origin: str = "real", channel: str = "texto") -> Sample:
    return Sample(id=id, channel=channel, content=f"mensagem {id}", label=label, origin=origin, source="teste")


def test_synthetic_samples_never_reach_the_test_split():
    samples = [sample(f"s{i}", origin="synthetic") for i in range(50)]
    splits = assign_splits(samples, test_ratio=0.5, seed=7)
    assert set(splits.values()) == {Split.TRAIN}


def test_split_is_stratified_by_channel_and_label():
    samples = [sample(f"g{i}", label="GOLPE") for i in range(20)] + [sample(f"s{i}", label="SEGURO") for i in range(10)]
    splits = assign_splits(samples, test_ratio=0.3, seed=7)
    test_labels = [s.label for s in samples if splits[s.id] is Split.TEST]
    assert test_labels.count("GOLPE") == 6
    assert test_labels.count("SEGURO") == 3


def test_split_is_fixed_by_seed_and_does_not_depend_on_input_order():
    samples = [sample(f"g{i}") for i in range(30)]
    first = assign_splits(samples, test_ratio=0.3, seed=42)
    assert assign_splits(list(reversed(samples)), test_ratio=0.3, seed=42) == first
    assert assign_splits(samples, test_ratio=0.3, seed=43) != first


def test_adding_a_sample_keeps_most_earlier_assignments():
    # A new real message must not reshuffle the whole test set.
    samples = [sample(f"g{i}") for i in range(40)]
    before = assign_splits(samples, test_ratio=0.3, seed=42)
    after = assign_splits(samples + [sample("novo")], test_ratio=0.3, seed=42)
    moved = [k for k in before if before[k] is not after[k]]
    assert len(moved) <= 1


def test_loader_rejects_samples_without_provenance(tmp_path):
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps([{"id": "x", "channel": "texto", "content": "oi", "label": "GOLPE"}]), encoding="utf-8")
    with pytest.raises(ValueError, match="origin"):
        load_samples(path)


def test_loader_rejects_duplicate_ids(tmp_path):
    item = {"id": "x", "channel": "texto", "content": "oi", "label": "GOLPE", "origin": "real", "source": "teste"}
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps([item, item]), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        load_samples(path)


def test_shipped_dataset_is_valid_and_labelled_honestly():
    samples = load_samples()
    assert samples
    # The hand-written seed messages are not real collected data, so they can only train.
    assert all(s.origin == "synthetic" for s in samples if s.source == "seed-autoral")
