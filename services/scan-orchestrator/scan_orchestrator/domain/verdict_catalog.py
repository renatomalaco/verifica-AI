from contracts import Persuasion, ThreatLevel, VerdictMessage

_SCAM_BY_PERSUASION: dict[Persuasion, VerdictMessage] = {
    Persuasion.AFFECTIVE_COERCION: VerdictMessage.SCAM_AFFECTIVE_COERCION,
    Persuasion.FINANCIAL_THREAT: VerdictMessage.SCAM_FINANCIAL_THREAT,
    Persuasion.URGENCY: VerdictMessage.SCAM_URGENCY,
}

_BY_THREAT: dict[ThreatLevel, VerdictMessage] = {
    ThreatLevel.SCAM: VerdictMessage.SCAM_GENERIC,
    ThreatLevel.CAUTION: VerdictMessage.CAUTION,
    ThreatLevel.SAFE: VerdictMessage.SAFE,
    ThreatLevel.INCONCLUSIVE: VerdictMessage.INCONCLUSIVE,
}


def verdict_message_for(
    threat: ThreatLevel,
    persuasion: Persuasion | None = None,
    category: str | None = None,
) -> VerdictMessage:
    """Picks the message code; the wording lives in the front end's dictionary."""
    if category == "brand_spoofing":
        return VerdictMessage.SCAM_BRAND_SPOOFING
    if threat is ThreatLevel.SCAM and persuasion in _SCAM_BY_PERSUASION:
        return _SCAM_BY_PERSUASION[persuasion]
    return _BY_THREAT[threat]
