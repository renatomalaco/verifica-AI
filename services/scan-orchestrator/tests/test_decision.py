import pytest
from contracts import ThreatLevel
from scan_orchestrator.domain.risk_score import RiskScore
from scan_orchestrator.domain.decision import ThresholdPolicy, decide


@pytest.mark.parametrize(
    "score_val,has_links,expected_threat",
    [
        (0.95, False, ThreatLevel.SCAM),
        (0.90, True, ThreatLevel.SCAM),
        (0.05, False, ThreatLevel.SAFE),
        (0.05, True, ThreatLevel.CAUTION),
        (0.10, False, ThreatLevel.SAFE),
        (0.50, False, ThreatLevel.CAUTION),
        (0.75, True, ThreatLevel.CAUTION),
    ],
)
def test_decision_logic(score_val: float, has_links: bool, expected_threat: ThreatLevel):
    policy = ThresholdPolicy(scam=0.90, safe=0.10)
    score = RiskScore(score_val)
    verdict = decide(score=score, has_links=has_links, policy=policy)
    assert verdict == expected_threat
