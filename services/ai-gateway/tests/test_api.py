import pytest
from httpx import AsyncClient, ASGITransport
from ai_gateway.api.main import (
    app,
    get_brand_catalog,
    get_brand_verifier,
    get_jev_client,
    get_settings,
    get_visual_embedder,
)
from ai_gateway.infrastructure.fakes import FakeBrandCatalog, FakeVisualEmbedder, one_hot
from ai_gateway.settings import Settings
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



BB_LOGO = one_hot(0, 768)


async def _post_brand_match(payload: dict):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.post("/v1/brand-match", json=payload)


@pytest.fixture
def brand_overrides():
    app.dependency_overrides[get_visual_embedder] = lambda: FakeVisualEmbedder(default_embedding=BB_LOGO)
    app.dependency_overrides[get_brand_catalog] = lambda: FakeBrandCatalog({"Banco do Brasil": [BB_LOGO]})
    app.dependency_overrides[get_brand_verifier] = lambda: None
    yield app.dependency_overrides
    app.dependency_overrides.clear()


async def test_brand_match_endpoint_detects_spoofing(brand_overrides):
    resp = await _post_brand_match({"image_b64": "aGVsbG8=", "current_domain": "bb-seguro-atualizacao.xyz"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["matched_brand"] == "Banco do Brasil"
    assert data["is_spoofing"] is True
    assert data["similarity"] >= 0.82


async def test_brand_match_with_an_empty_catalog_is_unavailable(brand_overrides):
    # "No brand found" would read as checked-and-clean; the orchestrator must see a failure.
    brand_overrides[get_brand_catalog] = lambda: FakeBrandCatalog({})

    resp = await _post_brand_match({"image_b64": "aGVsbG8=", "current_domain": "x.com"})

    assert resp.status_code == 503


async def test_brand_match_without_a_database_is_unavailable(brand_overrides):
    del brand_overrides[get_brand_catalog]
    brand_overrides[get_settings] = lambda: Settings(_env_file=None, DATABASE_URL="")

    resp = await _post_brand_match({"image_b64": "aGVsbG8=", "current_domain": "x.com"})

    assert resp.status_code == 503


def test_visual_rag_defaults_follow_the_plan():
    settings = Settings(_env_file=None)
    assert settings.BRAND_MATCH_THRESHOLD == 0.82
    assert settings.BRAND_GRAY_ZONE_FLOOR < settings.BRAND_MATCH_THRESHOLD
    assert settings.EMBEDDING_DIM == 768


def test_the_vlm_is_off_without_a_gemini_key():
    assert get_brand_verifier(Settings(_env_file=None, VLM_PROVIDER="gemini", GEMINI_API_KEY="")) is None
    assert get_brand_verifier(Settings(_env_file=None, VLM_PROVIDER="none", GEMINI_API_KEY="k")) is None
    assert get_brand_verifier(Settings(_env_file=None, VLM_PROVIDER="gemini", GEMINI_API_KEY="k")) is not None
