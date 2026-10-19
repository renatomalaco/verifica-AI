from contracts import ThreatLevel, Persuasion
from scan_orchestrator.domain.verdict_catalog import get_verdict_texts


def test_verdict_catalog_returns_warm_ptbr_texts():
    v_plain, advice = get_verdict_texts(ThreatLevel.SCAM, Persuasion.AFFECTIVE_COERCION)
    assert "falso parente" in v_plain.lower()
    assert "pix" in advice.lower()

    v_plain, advice = get_verdict_texts(ThreatLevel.SAFE, Persuasion.NONE)
    assert "não encontramos sinais de golpe" in v_plain.lower()
    assert "senhas" in advice.lower()

    v_plain, advice = get_verdict_texts(ThreatLevel.INCONCLUSIVE, None)
    assert "não foi possível concluir" in v_plain.lower()
    assert "precaução" in advice.lower()


def test_verdict_catalog_has_fallback_for_every_threat_level():
    for threat in ThreatLevel:
        v_plain, advice = get_verdict_texts(threat, None)
        assert len(v_plain) > 10
        assert len(advice) > 10
