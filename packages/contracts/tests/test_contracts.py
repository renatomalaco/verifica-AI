import pytest
from uuid import uuid4
from pydantic import ValidationError

from contracts import (
    ThreatLevel,
    Channel,
    Persuasion,
    ScanRequest,
    ScanDetails,
    ScanResponse,
    VerdictMessage,
    StageEvent,
    TriageRequest,
    TriageResult,
)


def test_threat_level_enum_values():
    assert ThreatLevel.SAFE == "SEGURO"
    assert ThreatLevel.CAUTION == "CUIDADO"
    assert ThreatLevel.SCAM == "GOLPE"
    assert ThreatLevel.INCONCLUSIVE == "INCONCLUSIVO"


def test_channel_enum_values():
    assert Channel.TEXT == "texto"
    assert Channel.URL == "url"
    assert Channel.IMAGE == "imagem"


def test_persuasion_enum_values():
    assert Persuasion.URGENCY == "urgencia"
    assert Persuasion.FINANCIAL_THREAT == "ameaca_financeira"
    assert Persuasion.AFFECTIVE_COERCION == "coercao_afetiva"
    assert Persuasion.NONE == "nenhuma"


def test_scan_request_valid():
    req = ScanRequest(content="Mensagem de teste")
    assert req.content == "Mensagem de teste"
    assert req.image_b64 is None


def test_scan_request_with_image():
    req = ScanRequest(content="", image_b64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
    assert req.image_b64 is not None


def test_scan_request_empty_content_and_no_image_fails():
    with pytest.raises(ValidationError):
        ScanRequest(content="")


def test_triage_result_valid():
    res = TriageResult(
        is_phishing=0.95,
        requires_visual_inspection=0.10,
        persuasion=Persuasion.URGENCY,
    )
    assert res.is_phishing == 0.95
    assert res.persuasion == Persuasion.URGENCY


def test_triage_result_out_of_bounds_score_fails():
    with pytest.raises(ValidationError):
        TriageResult(
            is_phishing=1.5,
            requires_visual_inspection=0.0,
            persuasion=Persuasion.NONE,
        )

    with pytest.raises(ValidationError):
        TriageResult(
            is_phishing=-0.1,
            requires_visual_inspection=0.0,
            persuasion=Persuasion.NONE,
        )


def test_scan_response_serialization():
    details = ScanDetails(
        channel=Channel.TEXT,
        deciding_stage="triage",
        category="coercao_afetiva",
        scores={"is_phishing": 0.92},
        domain_signals=None,
        links_not_inspected=False,
        latency_breakdown={"triage": 120.5},
    )
    resp = ScanResponse(
        id=uuid4(),
        threat_level=ThreatLevel.SCAM,
        verdict_message=VerdictMessage.SCAM_AFFECTIVE_COERCION,
        details=details,
    )
    assert resp.threat_level == ThreatLevel.SCAM
    assert resp.details.latency_breakdown["triage"] == 120.5


def test_stage_event_validation():
    event = StageEvent(stage="triage", status="started")
    assert event.stage == "triage"
    assert event.status == "started"

    with pytest.raises(ValidationError):
        StageEvent(stage="triage", status="invalid_status")
