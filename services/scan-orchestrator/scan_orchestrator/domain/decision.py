from dataclasses import dataclass
from contracts import ThreatLevel
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
