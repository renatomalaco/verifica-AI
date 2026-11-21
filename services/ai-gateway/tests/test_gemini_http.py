import time

import httpx
import pytest
import respx

from ai_gateway.infrastructure import gemini_http
from ai_gateway.infrastructure.gemini_http import generate_content

GEMINI_BASE = "https://gemini.test"
ROUTE = "/v1beta/models/gemini-x:generateContent"


async def _call(timeout_seconds: float = 5.0) -> dict:
    return await generate_content(GEMINI_BASE, "k", "gemini-x", timeout_seconds, {"contents": []})


@pytest.fixture(autouse=True)
def short_pause(monkeypatch):
    monkeypatch.setattr(gemini_http, "RETRY_PAUSE_SECONDS", 0.05)


async def test_an_overloaded_answer_is_tried_again():
    # On the free tier Google often answers 503 in 1-3 s and then answers the same request.
    async with respx.mock(base_url=GEMINI_BASE) as mock:
        route = mock.post(ROUTE)
        route.side_effect = [httpx.Response(503), httpx.Response(200, json={"ok": True})]

        assert await _call() == {"ok": True}
        assert route.call_count == 2


async def test_retries_stop_at_the_calls_own_deadline():
    # The callers' timeouts (gateway budget, orchestrator wait) must still hold.
    async with respx.mock(base_url=GEMINI_BASE) as mock:
        mock.post(ROUTE).respond(503)
        started = time.monotonic()

        with pytest.raises(RuntimeError):
            await _call(timeout_seconds=0.5)

        assert time.monotonic() - started < 1.0


@pytest.mark.parametrize("status", [429, 500])
async def test_other_errors_are_not_tried_again(status):
    # 429 is our own quota: asking again right away only spends it.
    async with respx.mock(base_url=GEMINI_BASE) as mock:
        route = mock.post(ROUTE).respond(status)

        with pytest.raises(RuntimeError):
            await _call()
        assert route.call_count == 1


async def test_a_timeout_is_not_tried_again():
    async with respx.mock(base_url=GEMINI_BASE) as mock:
        route = mock.post(ROUTE).mock(side_effect=httpx.ReadTimeout("lento"))

        with pytest.raises(RuntimeError, match="timed out"):
            await _call()
        assert route.call_count == 1
