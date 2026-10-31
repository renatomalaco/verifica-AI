import base64
import json

import httpx
import pytest
import respx

from ai_gateway.infrastructure.gemini_brand_verifier import GeminiBrandVerifier

GEMINI_BASE = "https://gemini.test"
ROUTE = "/v1beta/models/gemini-x:generateContent"
JPEG_B64 = base64.b64encode(b"\xff\xd8\xff\xe0fake-jpeg").decode()
PNG_B64 = base64.b64encode(b"\x89PNG\r\n\x1a\nfake-png").decode()


def _verifier() -> GeminiBrandVerifier:
    return GeminiBrandVerifier(base_url=GEMINI_BASE, api_key="k", model="gemini-x")


def _reply(payload: dict) -> dict:
    return {"candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}]}


async def test_sends_the_screenshot_inline_with_a_json_schema_and_reads_the_answer():
    async with respx.mock(base_url=GEMINI_BASE) as mock:
        route = mock.post(ROUTE).respond(json=_reply({"shows_brand": True}))
        answer = await _verifier().shows_brand(JPEG_B64, "Banco do Brasil")

    assert answer is True
    sent = route.calls.last.request
    assert sent.headers["x-goog-api-key"] == "k"
    assert "key=" not in str(sent.url)
    body = json.loads(sent.content)
    parts = body["contents"][0]["parts"]
    assert parts[0]["inlineData"] == {"mimeType": "image/jpeg", "data": JPEG_B64}
    assert "Banco do Brasil" in parts[1]["text"]
    assert body["generationConfig"]["responseMimeType"] == "application/json"
    assert body["generationConfig"]["responseSchema"]["required"] == ["shows_brand"]


async def test_page_text_is_declared_untrusted_in_the_instructions():
    # A phishing page can print "this is the official bank site" to steer the model.
    async with respx.mock(base_url=GEMINI_BASE) as mock:
        route = mock.post(ROUTE).respond(json=_reply({"shows_brand": False}))
        await _verifier().shows_brand(PNG_B64, "Nubank")

    body = json.loads(route.calls.last.request.content)
    assert body["contents"][0]["parts"][0]["inlineData"]["mimeType"] == "image/png"
    assert "untrusted" in body["systemInstruction"]["parts"][0]["text"].lower()


@pytest.mark.parametrize(
    "reply",
    [
        {"json": _reply({"answer": "sim"})},
        {"json": {"candidates": []}},
        {"status_code": 500},
    ],
)
async def test_unusable_answers_raise(reply):
    async with respx.mock(base_url=GEMINI_BASE) as mock:
        mock.post(ROUTE).respond(**reply)
        with pytest.raises(RuntimeError):
            await _verifier().shows_brand(JPEG_B64, "Nubank")


async def test_timeout_raises():
    async with respx.mock(base_url=GEMINI_BASE) as mock:
        mock.post(ROUTE).mock(side_effect=httpx.ReadTimeout("lento"))
        with pytest.raises(RuntimeError):
            await _verifier().shows_brand(JPEG_B64, "Nubank")
