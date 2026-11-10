import json

import httpx
import pytest
import respx
from contracts import Persuasion

from ai_gateway.infrastructure.gemini_triage_client import GeminiTriageClient

GEMINI_BASE = "https://gemini.test"
ROUTE = "/v1beta/models/gemini-x:generateContent"
ENVELOPE = "<untrusted_inspection_data>Oi mãe, me faz um pix urgente</untrusted_inspection_data>"
USAGE = {"promptTokenCount": 120, "candidatesTokenCount": 30, "thoughtsTokenCount": 50, "totalTokenCount": 200}
ANSWER = {"is_phishing": 0.97, "requires_visual_inspection": 0.1, "persuasion": "coercao_afetiva"}


def _client() -> GeminiTriageClient:
    return GeminiTriageClient(base_url=GEMINI_BASE, api_key="k", model="gemini-x")


def _reply(answer: object, usage: dict | None = USAGE) -> dict:
    reply: dict = {"candidates": [{"content": {"parts": [{"text": json.dumps(answer)}]}}]}
    if usage is not None:
        reply["usageMetadata"] = usage
    return reply


async def test_sends_the_envelope_with_a_json_schema_and_reads_the_triage():
    async with respx.mock(base_url=GEMINI_BASE) as mock:
        route = mock.post(ROUTE).respond(json=_reply(ANSWER))
        result = await _client().classify(ENVELOPE)

    assert result.is_phishing == 0.97
    assert result.persuasion is Persuasion.AFFECTIVE_COERCION
    sent = route.calls.last.request
    assert sent.headers["x-goog-api-key"] == "k"
    assert "key=" not in str(sent.url)
    body = json.loads(sent.content)
    assert body["contents"][0]["parts"][0]["text"] == ENVELOPE
    assert "untrusted_inspection_data" in body["systemInstruction"]["parts"][0]["text"]
    assert body["generationConfig"]["responseMimeType"] == "application/json"
    assert set(body["generationConfig"]["responseSchema"]["required"]) == {
        "is_phishing",
        "requires_visual_inspection",
        "persuasion",
    }


async def test_measure_reports_billed_tokens_with_thinking_as_output():
    async with respx.mock(base_url=GEMINI_BASE) as mock:
        mock.post(ROUTE).respond(json=_reply(ANSWER))
        measured = await _client().measure(ENVELOPE)

    assert measured.result.is_phishing == 0.97
    assert measured.input_tokens == 120
    assert measured.output_tokens == 80  # thinking tokens are billed at the output price


@pytest.mark.parametrize(
    "reply",
    [
        {"json": _reply({"is_phishing": "alta"})},
        {"json": _reply({**ANSWER, "is_phishing": 1.4})},
        {"json": _reply(ANSWER, usage=None)},
        {"json": {"candidates": []}},
        {"text": "not json"},
        {"status_code": 429},
        {"status_code": 500},
    ],
)
async def test_unusable_answers_raise(reply):
    async with respx.mock(base_url=GEMINI_BASE) as mock:
        mock.post(ROUTE).respond(**reply)
        with pytest.raises(RuntimeError):
            await _client().measure(ENVELOPE)


async def test_timeout_raises():
    async with respx.mock(base_url=GEMINI_BASE) as mock:
        mock.post(ROUTE).mock(side_effect=httpx.ReadTimeout("lento"))
        with pytest.raises(RuntimeError):
            await _client().classify(ENVELOPE)
