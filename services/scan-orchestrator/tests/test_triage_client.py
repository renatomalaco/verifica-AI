import logging

import httpx
import respx

from scan_orchestrator.infrastructure.triage_client import HttpTriageClient

GATEWAY = "http://gateway.test"
ANSWER = {"is_phishing": 0.99, "requires_visual_inspection": 0.0, "persuasion": "coercao_afetiva"}
TEXT = "oi pai, troquei de número. Me faz um pix?"


async def test_each_depth_calls_its_own_route():
    client = HttpTriageClient(base_url=GATEWAY)
    async with respx.mock(base_url=GATEWAY) as mock:
        quick = mock.post("/v1/triage").respond(json=ANSWER)
        deep = mock.post("/v1/triage/deep").respond(json=ANSWER)

        await client.triage(TEXT)
        await client.deep_triage(TEXT)

    assert quick.call_count == 1
    assert deep.call_count == 1


async def test_an_unavailable_gateway_is_logged_without_the_text(caplog):
    client = HttpTriageClient(base_url=GATEWAY)
    with caplog.at_level(logging.WARNING):
        async with respx.mock(base_url=GATEWAY) as mock:
            mock.post("/v1/triage").respond(503)
            mock.post("/v1/triage/deep").mock(side_effect=httpx.ReadTimeout("slow"))

            assert await client.triage(TEXT) is None
            assert await client.deep_triage(TEXT) is None

    assert "503" in caplog.text
    assert "ReadTimeout" in caplog.text
    assert "pix" not in caplog.text
