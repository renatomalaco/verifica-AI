"""Adversarial robustness: the same detector, with and without input sanitization."""

from collections.abc import Callable
from dataclasses import dataclass

from research_runner.domain.dataset import Sample

SCAM_THRESHOLD = 0.5


@dataclass(frozen=True)
class AdversarialResult:
    total: int
    detected_without_sanitization: int
    detected_with_sanitization: int


def evaluate_adversarial(
    samples: list[Sample],
    scam_probability: Callable[[str], float],
    sanitize: Callable[[str], str],
) -> AdversarialResult:
    """Counts adversarial scams caught on the raw text versus the sanitized text."""
    attacks = [s for s in samples if s.adversarial and s.label == "GOLPE"]
    raw = sum(1 for s in attacks if scam_probability(s.content) >= SCAM_THRESHOLD)
    clean = sum(1 for s in attacks if scam_probability(sanitize(s.content)) >= SCAM_THRESHOLD)
    return AdversarialResult(total=len(attacks), detected_without_sanitization=raw, detected_with_sanitization=clean)
