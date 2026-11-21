from dataclasses import dataclass
from contracts import ThreatLevel, TriageResult
from scan_orchestrator.domain.risk_score import RiskScore


@dataclass(frozen=True)
class ThresholdPolicy:
    scam: float = 0.90
    safe: float = 0.10


def decide(score: RiskScore, has_unverified_links: bool, policy: ThresholdPolicy) -> ThreatLevel:
    """
    Applies the cascade cutoff logic for defense in depth,
    using guard clauses and early returns (no 'else').
    """
    if score.value >= policy.scam:
        return ThreatLevel.SCAM

    if score.value <= policy.safe:
        # Ethical guideline: never issue SEGURO while a link could not be verified.
        # A link that was inspected and found safe does not hold the verdict back.
        if has_unverified_links:
            return ThreatLevel.CAUTION
        return ThreatLevel.SAFE

    return ThreatLevel.CAUTION


def needs_confirmation(quick: TriageResult, policy: ThresholdPolicy) -> bool:
    """Only a clear scam stands on the quick model: a false GOLPE harms less than a false SEGURO,
    so doubt and every would-be SEGURO go to the deep model."""
    return quick.is_phishing < policy.scam


def settle(
    quick: TriageResult, deep: TriageResult | None, policy: ThresholdPolicy
) -> TriageResult | None:
    """The deep answer wins. Without it, an unconfirmed SEGURO is doubt (None, INCONCLUSIVO)
    and an unconfirmed doubt keeps the quick answer (CUIDADO)."""
    if deep is not None:
        return deep
    if quick.is_phishing <= policy.safe:
        return None
    return quick


MIN_OCR_CONFIDENCE = 60.0


def ocr_is_reliable(confidence: float | None) -> bool:
    """A screenshot read with doubt may hide the scam: it can hold a verdict back, never
    clear it."""
    return confidence is not None and confidence >= MIN_OCR_CONFIDENCE
