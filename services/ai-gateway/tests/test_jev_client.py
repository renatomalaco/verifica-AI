import pytest
import respx
import httpx
from contracts import Persuasion
from ai_gateway.infrastructure.jev_client import FakeJevClient, HttpJevClient


@pytest.mark.asyncio
async def test_fake_jev_client_detects_coercion_scam():
    client = FakeJevClient()
    envelope = "<untrusted_inspection_data>Oi mãe, troquei de número, me faz um pix urgente</untrusted_inspection_data>"
    result = await client.classify(envelope)
    assert result.is_phishing >= 0.90
    assert result.persuasion == Persuasion.AFFECTIVE_COERCION


@pytest.mark.asyncio
async def test_fake_jev_client_detects_safe_message():
    client = FakeJevClient()
    envelope = "<untrusted_inspection_data>Bom dia equipe, nossa reunião semanal será às 14h na sala 3.</untrusted_inspection_data>"
    result = await client.classify(envelope)
    assert result.is_phishing <= 0.10
    assert result.persuasion == Persuasion.NONE


@pytest.mark.asyncio
async def test_http_jev_client_success():
    client = HttpJevClient(base_url="https://mock-jev.api", api_key="test-key")
    async with respx.mock(base_url="https://mock-jev.api") as mock:
        mock.post("/v1/systemone").respond(
            json={
                "answers": {
                    "is_phishing": {"probability": 0.94},
                    "requires_visual_inspection": {"probability": 0.05},
                    "persuasion": {"selected": "urgencia"},
                }
            }
        )
        envelope = "<untrusted_inspection_data>Aviso de bloqueio bancário</untrusted_inspection_data>"
        result = await client.classify(envelope)
        assert result.is_phishing == 0.94
        assert result.requires_visual_inspection == 0.05
        assert result.persuasion == Persuasion.URGENCY


@pytest.mark.asyncio
async def test_http_jev_client_timeout_raises_runtime_error():
    client = HttpJevClient(base_url="https://mock-jev.api", api_key="test-key", timeout_seconds=0.1)
    async with respx.mock(base_url="https://mock-jev.api") as mock:
        mock.post("/v1/systemone").mock(side_effect=httpx.TimeoutException("Timeout"))
        with pytest.raises(RuntimeError) as exc_info:
            await client.classify("<untrusted_inspection_data>qualquer</untrusted_inspection_data>")
        assert "Timeout na consulta ao modelo Jev" in str(exc_info.value)
