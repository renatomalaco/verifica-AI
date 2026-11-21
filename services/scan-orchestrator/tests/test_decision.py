import pytest
from contracts import Persuasion, ThreatLevel, TriageResult
from scan_orchestrator.domain.risk_score import RiskScore
from scan_orchestrator.domain.decision import ThresholdPolicy, decide, needs_confirmation, settle


@pytest.mark.parametrize(
    "score_val,has_unverified_links,expected_threat",
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
def test_decision_logic(score_val: float, has_unverified_links: bool, expected_threat: ThreatLevel):
    policy = ThresholdPolicy(scam=0.90, safe=0.10)
    score = RiskScore(score_val)
    verdict = decide(score=score, has_unverified_links=has_unverified_links, policy=policy)
    assert verdict == expected_threat


QUICK_DOUBT = TriageResult(is_phishing=0.50, persuasion=Persuasion.URGENCY)
QUICK_SAFE = TriageResult(is_phishing=0.05)
DEEP = TriageResult(is_phishing=0.97, persuasion=Persuasion.AFFECTIVE_COERCION)
POLICY = ThresholdPolicy(scam=0.90, safe=0.10)


@pytest.mark.parametrize(
    "score,needs_deep", [(0.99, False), (0.90, False), (0.89, True), (0.50, True), (0.05, True)]
)
def test_only_a_clear_scam_stands_on_the_quick_model(score: float, needs_deep: bool):
    assert needs_confirmation(TriageResult(is_phishing=score), POLICY) is needs_deep


@pytest.mark.parametrize("quick", [QUICK_DOUBT, QUICK_SAFE])
def test_the_deep_answer_settles_the_triage(quick: TriageResult):
    assert settle(quick, DEEP, POLICY) == DEEP


def test_an_unconfirmed_safe_answer_becomes_unknown_never_seguro():
    assert settle(QUICK_SAFE, None, POLICY) is None


def test_an_unconfirmed_doubt_keeps_the_quick_answer():
    assert settle(QUICK_DOUBT, None, POLICY) == QUICK_DOUBT
