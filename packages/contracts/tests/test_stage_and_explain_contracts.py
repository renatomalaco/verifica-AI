import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from contracts import (
    Channel,
    ExplainRequest,
    ExplainResponse,
    ExplainResult,
    QuotaExceeded,
    StageEvent,
    StageName,
    ThreatLevel,
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
        verdict_plain="É golpe.",
        action_advice="Não clique.",
    )
    # There is no field for the raw content sent by the person (LGPD).
    assert "content" not in ExplainRequest.model_fields
    assert req.scores == {}
    assert req.domain_signals == {}


def test_explain_result_requires_at_least_one_line():
    with pytest.raises(ValidationError):
        ExplainResult(lines=[])


def test_explain_response_and_quota_exceeded_shapes():
    resp = ExplainResponse(lines=["a"], remaining_today=2)
    assert resp.model_dump() == {"lines": ["a"], "remaining_today": 2}

    retry = datetime(2026, 10, 17, 3, 0, tzinfo=timezone.utc)
    body = json.loads(QuotaExceeded(retry_at=retry).model_dump_json())
    assert body == {"retry_at": "2026-10-17T03:00:00Z"}
