import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from contracts import (
    Channel,
    ExplainRequest,
    ExplainResponse,
    ExplainResult,
    ExplainScanRequest,
    Locale,
    QuotaExceeded,
    ScanResponse,
    StageEvent,
    StageName,
    ThreatLevel,
    VerdictMessage,
    resolve_locale,
)


def test_stage_name_values_match_frontend_contract():
    # These values are consumed by web/src/utils/stages.ts; changing them breaks the front end.
    assert [s.value for s in StageName] == [
        "triage",
        "image_extraction",
        "stage_0_cache",
        "stage_1_signals",
        "stage_2_inspection",
        "visual_rag",
    ]


def test_stage_event_accepts_known_stage_and_serializes_as_plain_string():
    event = StageEvent(stage=StageName.VISUAL_RAG, status="done")
    assert json.loads(event.model_dump_json()) == {"stage": "visual_rag", "status": "done"}


def test_stage_event_rejects_unknown_stage():
    with pytest.raises(ValidationError):
        StageEvent(stage="url_cascade", status="started")


def test_explain_request_carries_only_the_persisted_verdict():
    req = ExplainRequest(
        threat_level=ThreatLevel.SCAM,
        channel=Channel.URL,
        deciding_stage="stage_0_blacklist_feed",
        category="blacklist_feed",
        verdict_message=VerdictMessage.SCAM_GENERIC,
    )
    # There is no field for the raw content sent by the person (LGPD).
    assert "content" not in ExplainRequest.model_fields
    assert req.scores == {}
    assert req.domain_signals == {}
    assert req.locale is Locale.PT_BR


def test_explain_result_requires_at_least_one_line():
    with pytest.raises(ValidationError):
        ExplainResult(lines=[])


def test_explain_response_and_quota_exceeded_shapes():
    resp = ExplainResponse(lines=["a"], remaining_today=2)
    assert resp.model_dump() == {"lines": ["a"], "remaining_today": 2}

    retry = datetime(2026, 10, 17, 3, 0, tzinfo=timezone.utc)
    body = json.loads(QuotaExceeded(retry_at=retry).model_dump_json())
    assert body == {"retry_at": "2026-10-17T03:00:00Z"}


def test_verdict_message_values_match_frontend_dictionary():
    # Keys of web/src/domain/verdictMessages.ts; the backend decides, the front end words it.
    assert [m.value for m in VerdictMessage] == [
        "scam_affective_coercion",
        "scam_financial_threat",
        "scam_urgency",
        "scam_brand_spoofing",
        "scam_generic",
        "caution",
        "safe",
        "inconclusive",
    ]


def test_scan_response_carries_a_message_code_instead_of_text():
    assert "verdict_message" in ScanResponse.model_fields
    assert "verdict_plain" not in ScanResponse.model_fields
    assert "action_advice" not in ScanResponse.model_fields


def test_resolve_locale_falls_back_to_brazilian_portuguese():
    assert resolve_locale("pt-BR") is Locale.PT_BR
    assert resolve_locale("pt-br") is Locale.PT_BR
    assert resolve_locale("xx-YY") is Locale.PT_BR
    assert resolve_locale(None) is Locale.PT_BR


def test_explain_scan_request_defaults_to_brazilian_portuguese():
    assert ExplainScanRequest().locale is Locale.PT_BR
    assert ExplainScanRequest(locale="zz").locale is Locale.PT_BR
