from contracts import Persuasion, ThreatLevel, VerdictMessage
from scan_orchestrator.domain.verdict_catalog import verdict_message_for


def test_scam_message_follows_the_persuasion_technique():
    assert (
        verdict_message_for(ThreatLevel.SCAM, Persuasion.AFFECTIVE_COERCION)
        is VerdictMessage.SCAM_AFFECTIVE_COERCION
    )
    assert (
        verdict_message_for(ThreatLevel.SCAM, Persuasion.FINANCIAL_THREAT)
        is VerdictMessage.SCAM_FINANCIAL_THREAT
    )
    assert verdict_message_for(ThreatLevel.SCAM, Persuasion.URGENCY) is VerdictMessage.SCAM_URGENCY
    assert verdict_message_for(ThreatLevel.SCAM, Persuasion.NONE) is VerdictMessage.SCAM_GENERIC
    assert verdict_message_for(ThreatLevel.SCAM, None) is VerdictMessage.SCAM_GENERIC


def test_brand_spoofing_wins_over_persuasion():
    message = verdict_message_for(ThreatLevel.SCAM, Persuasion.URGENCY, category="brand_spoofing")
    assert message is VerdictMessage.SCAM_BRAND_SPOOFING


def test_persuasion_does_not_turn_a_non_scam_into_a_scam_message():
    assert verdict_message_for(ThreatLevel.SAFE, Persuasion.URGENCY) is VerdictMessage.SAFE
    assert (
        verdict_message_for(ThreatLevel.CAUTION, Persuasion.AFFECTIVE_COERCION)
        is VerdictMessage.CAUTION
    )
    assert verdict_message_for(ThreatLevel.INCONCLUSIVE, None) is VerdictMessage.INCONCLUSIVE


def test_every_threat_level_has_a_message():
    for threat in ThreatLevel:
        assert isinstance(verdict_message_for(threat, None), VerdictMessage)


def test_the_own_address_gets_a_message_that_names_the_product():
    message = verdict_message_for(ThreatLevel.SAFE, None, category="own_address")
    assert message is VerdictMessage.SAFE_OWN_ADDRESS


def test_an_official_address_gets_a_message_about_the_registry_not_about_safety():
    message = verdict_message_for(ThreatLevel.SAFE, None, category="official_address")
    assert message is VerdictMessage.SAFE_OFFICIAL_ADDRESS


def test_a_scam_link_gets_a_message_about_the_link_not_about_money():
    # A fake DETRAN link only redirects; saying "it pressures you to pay" would be wrong.
    message = verdict_message_for(
        ThreatLevel.SCAM, Persuasion.FINANCIAL_THREAT, category="embedded_phishing_link"
    )
    assert message is VerdictMessage.SCAM_PHISHING_LINK
