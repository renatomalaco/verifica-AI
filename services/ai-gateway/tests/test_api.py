import pytest
from httpx import AsyncClient, ASGITransport
from ai_gateway.api.main import app, get_jev_client
from contracts import TriageResult, Persuasion


class SpyJevClient:
    def __init__(self):
        self.received_envelope = ""

    async def classify(self, envelope: str) -> TriageResult:
        self.received_envelope = envelope
        return TriageResult(
            is_phishing=0.95,
            requires_visual_inspection=0.01,
            persuasion=Persuasion.URGENCY,
        )


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok", "service": "ai-gateway"}


@pytest.mark.asyncio
async def test_triage_masks_pii_before_jev():
    spy = SpyJevClient()
    app.dependency_overrides[get_jev_client] = lambda: spy

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/v1/triage",
                json={"text": "Faça o pix de R$ 50 para o CPF 123.456.789-00 urgente!"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["is_phishing"] == 0.95
            assert data["persuasion"] == "urgencia"

            assert "123.456.789-00" not in spy.received_envelope
            assert "[CPF_MASCARADO]" in spy.received_envelope
            assert "<untrusted_inspection_data>" in spy.received_envelope
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_brand_match_endpoint_detects_spoofing():
    from ai_gateway.api.main import get_visual_embedder
    from ai_gateway.domain.visual_embedder import FakeVisualEmbedder

    fake_emb = FakeVisualEmbedder(default_embedding=[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    app.dependency_overrides[get_visual_embedder] = lambda: fake_emb

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/v1/brand-match",
                json={
                    "image_b64": "fake_b64_logo_bb",
                    "current_domain": "bb-seguro-atualizacao.xyz",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["matched_brand"] == "Banco do Brasil"
            assert data["is_spoofing"] is True
            assert data["similarity"] >= 0.85
    finally:
        app.dependency_overrides.clear()
