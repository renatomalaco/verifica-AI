import pytest
from httpx import AsyncClient, ASGITransport
from ai_gateway.api.main import (
    app,
    get_brand_catalog,
    get_brand_verifier,
    get_deep_triage_client,
    get_triage_client,
    get_settings,
    get_visual_embedder,
)
from ai_gateway.infrastructure.fakes import FakeBrandCatalog, FakeVisualEmbedder, one_hot
from ai_gateway.settings import Settings
from contracts import TriageResult, Persuasion
from pydantic import ValidationError

from ai_gateway.application.triage_with_reserve import TriageWithReserve

GEMINI_TRIAGE = dict(
    AI_PROVIDER="gemini", GEMINI_API_KEY="k", GEMINI_MODEL="lite", GEMINI_DEEP_MODEL="flash"
)


class SpyTriageClient:
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
async def test_triage_masks_pii_before_the_model():
    spy = SpyTriageClient()
    app.dependency_overrides[get_triage_client] = lambda: spy

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


class FailingTriageClient:
    async def classify(self, envelope: str) -> TriageResult:
        raise RuntimeError("Gemini request timed out (6.0s)")


async def _post_triage(path: str, text: str = "Oi pai, troquei de número. Me faz um pix?"):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.post(path, json={"text": text})


@pytest.mark.parametrize(
    "path,dependency",
    [("/v1/triage", get_triage_client), ("/v1/triage/deep", get_deep_triage_client)],
)
async def test_a_failing_model_answers_503_not_a_crash(path, dependency):
    app.dependency_overrides[dependency] = FailingTriageClient
    try:
        resp = await _post_triage(path)
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 503


async def test_deep_triage_uses_its_own_model_and_masks_pii():
    spy = SpyTriageClient()
    app.dependency_overrides[get_deep_triage_client] = lambda: spy
    try:
        resp = await _post_triage("/v1/triage/deep", "Pix para o CPF 123.456.789-00")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert "[CPF_MASCARADO]" in spy.received_envelope


BB_LOGO = one_hot(0, 768)


async def _post_brand_match(payload: dict):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.post("/v1/brand-match", json=payload)


@pytest.fixture
def brand_overrides():
    app.dependency_overrides[get_visual_embedder] = lambda: FakeVisualEmbedder(
        default_embedding=BB_LOGO
    )
    app.dependency_overrides[get_brand_catalog] = lambda: FakeBrandCatalog(
        {"Banco do Brasil": [BB_LOGO]}
    )
    app.dependency_overrides[get_brand_verifier] = lambda: None
    # The author's .env may point at real providers; these tests never depend on it.
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)
    yield app.dependency_overrides
    app.dependency_overrides.clear()


async def test_brand_match_endpoint_detects_spoofing(brand_overrides):
    resp = await _post_brand_match(
        {"image_b64": "aGVsbG8=", "current_domain": "bb-seguro-atualizacao.xyz"}
    )

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
    assert (
        get_brand_verifier(Settings(_env_file=None, VLM_PROVIDER="gemini", GEMINI_API_KEY=""))
        is None
    )
    assert (
        get_brand_verifier(Settings(_env_file=None, VLM_PROVIDER="none", GEMINI_API_KEY="k"))
        is None
    )
    assert (
        get_brand_verifier(
            Settings(_env_file=None, VLM_PROVIDER="gemini", GEMINI_API_KEY="k", GEMINI_MODEL="m")
        )
        is not None
    )


def test_triage_provider_follows_ai_provider():
    from ai_gateway.infrastructure.gemini_triage_client import GeminiTriageClient
    from ai_gateway.infrastructure.fakes import FakeTriageClient

    gemini = Settings(_env_file=None, **GEMINI_TRIAGE)
    keyless = Settings(_env_file=None, AI_PROVIDER="gemini", GEMINI_API_KEY="")
    removed_jev = Settings(_env_file=None, AI_PROVIDER="jev", GEMINI_API_KEY="k")

    assert isinstance(get_triage_client(gemini), GeminiTriageClient)
    assert isinstance(get_triage_client(keyless), FakeTriageClient)
    assert isinstance(get_deep_triage_client(keyless), FakeTriageClient)
    # The Jev provider was removed: an old .env never reaches a paid API by accident.
    assert isinstance(get_triage_client(removed_jev), FakeTriageClient)


def test_each_triage_depth_calls_its_own_model_and_timeout():
    settings = Settings(_env_file=None, **GEMINI_TRIAGE)

    quick, deep = get_triage_client(settings), get_deep_triage_client(settings)

    assert (quick._model, quick._timeout_seconds) == (
        "lite",
        settings.GEMINI_TRIAGE_TIMEOUT_SECONDS,
    )
    assert (deep._model, deep._timeout_seconds) == ("flash", settings.GEMINI_DEEP_TIMEOUT_SECONDS)


def test_the_reserve_model_backs_the_quick_triage_only_when_configured():
    with_reserve = Settings(_env_file=None, **GEMINI_TRIAGE, GEMINI_FALLBACK_MODEL="other-lite")

    assert isinstance(get_triage_client(with_reserve), TriageWithReserve)


def test_the_reserve_model_also_backs_the_confirmation():
    # On the free tier the bigger model often answers 503: a second opinion beats INCONCLUSIVO.
    settings = Settings(_env_file=None, **GEMINI_TRIAGE, GEMINI_FALLBACK_MODEL="other-lite")

    deep = get_deep_triage_client(settings)

    assert isinstance(deep, TriageWithReserve)
    assert (deep._primary._model, deep._reserve._model) == ("flash", "other-lite")


def test_each_triage_call_fits_the_orchestrator_wait():
    # The orchestrator waits 20 s per call (quick, then deep): each one, with its reserve and
    # its 503 retries, must fit, or a slow model turns into INCONCLUSIVO again.
    settings = Settings(_env_file=None)

    quick_with_reserve = 2 * settings.GEMINI_TRIAGE_TIMEOUT_SECONDS
    deep_with_reserve = (
        settings.GEMINI_DEEP_TIMEOUT_SECONDS + settings.GEMINI_TRIAGE_TIMEOUT_SECONDS
    )
    assert max(quick_with_reserve, deep_with_reserve) <= 20.0


def test_the_deep_model_gets_time_for_a_bigger_model():
    # gemini-3.5-flash answered in 2.6 to 9.2 s on the VM (2026-11-21).
    assert Settings(_env_file=None).GEMINI_DEEP_TIMEOUT_SECONDS >= 10.0


@pytest.mark.parametrize("provider", ["AI_PROVIDER", "EXPLAIN_PROVIDER", "VLM_PROVIDER"])
def test_gemini_without_a_model_fails_at_startup(provider):
    # A model name baked into the code outlives the model: Google retired gemini-2.5-flash
    # (404) and every triage silently became INCONCLUSIVO.
    with pytest.raises(ValidationError, match="GEMINI_MODEL"):
        Settings(_env_file=None, GEMINI_API_KEY="k", **{provider: "gemini"})


def test_gemini_triage_without_a_deep_model_fails_at_startup():
    # Without it no answer could be confirmed, so nothing would ever be SEGURO.
    with pytest.raises(ValidationError, match="GEMINI_DEEP_MODEL"):
        Settings(_env_file=None, AI_PROVIDER="gemini", GEMINI_API_KEY="k", GEMINI_MODEL="lite")


def test_without_a_gemini_key_no_model_is_needed():
    assert Settings(_env_file=None, AI_PROVIDER="gemini", GEMINI_API_KEY="").GEMINI_MODEL == ""
