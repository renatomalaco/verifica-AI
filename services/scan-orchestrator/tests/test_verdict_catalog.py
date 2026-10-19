from contracts import Persuasion, ThreatLevel, VerdictMessage
from scan_orchestrator.domain.verdict_catalog import verdict_message_for


def test_scam_message_follows_the_persuasion_technique():
    assert verdict_message_for(ThreatLevel.SCAM, Persuasion.AFFECTIVE_COERCION) is VerdictMessage.SCAM_AFFECTIVE_COERCION
    assert verdict_message_for(ThreatLevel.SCAM, Persuasion.FINANCIAL_THREAT) is VerdictMessage.SCAM_FINANCIAL_THREAT
    assert verdict_message_for(ThreatLevel.SCAM, Persuasion.URGENCY) is VerdictMessage.SCAM_URGENCY
    assert verdict_message_for(ThreatLevel.SCAM, Persuasion.NONE) is VerdictMessage.SCAM_GENERIC
    assert verdict_message_for(ThreatLevel.SCAM, None) is VerdictMessage.SCAM_GENERIC


def test_brand_spoofing_wins_over_persuasion():
    message = verdict_message_for(ThreatLevel.SCAM, Persuasion.URGENCY, category="brand_spoofing")
    assert message is VerdictMessage.SCAM_BRAND_SPOOFING


def test_persuasion_does_not_turn_a_non_scam_into_a_scam_message():
    assert verdict_message_for(ThreatLevel.SAFE, Persuasion.URGENCY) is VerdictMessage.SAFE
    assert verdict_message_for(ThreatLevel.CAUTION, Persuasion.AFFECTIVE_COERCION) is VerdictMessage.CAUTION
    assert verdict_message_for(ThreatLevel.INCONCLUSIVE, None) is VerdictMessage.INCONCLUSIVE


def test_every_threat_level_has_a_message():
    for threat in ThreatLevel:
        assert isinstance(verdict_message_for(threat, None), VerdictMessage)
