import pytest
from contracts import Persuasion

from ai_gateway.infrastructure.fakes import FakeTriageClient


@pytest.mark.asyncio
async def test_fake_triage_client_detects_coercion_scam():
    envelope = (
        "<untrusted_inspection_data>Oi mãe, troquei de número, me faz um pix urgente"
        "</untrusted_inspection_data>"
    )

    result = await FakeTriageClient().classify(envelope)

    assert result.is_phishing >= 0.90
    assert result.persuasion == Persuasion.AFFECTIVE_COERCION


@pytest.mark.asyncio
async def test_fake_triage_client_detects_safe_message():
    envelope = (
        "<untrusted_inspection_data>Bom dia equipe, nossa reunião semanal será às 14h na sala 3."
        "</untrusted_inspection_data>"
    )

    result = await FakeTriageClient().classify(envelope)

    assert result.is_phishing <= 0.10
    assert result.persuasion == Persuasion.NONE
