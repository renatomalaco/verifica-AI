import pytest
from httpx import AsyncClient, ASGITransport
from scan_orchestrator.api.dependencies import get_triage_client
from scan_orchestrator.api.main import app
from contracts import TriageResult, Persuasion


class MockTriageClient:
    def __init__(self, is_phishing=0.95, persuasion=Persuasion.URGENCY):
        self.is_phishing = is_phishing
        self.persuasion = persuasion

    async def triage(self, text: str) -> TriageResult | None:
        return TriageResult(
            is_phishing=self.is_phishing,
            requires_visual_inspection=0.0,
            persuasion=self.persuasion,
        )


@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok", "service": "scan-orchestrator"}


@pytest.mark.asyncio
async def test_scan_text_returns_json_verdict():
    app.dependency_overrides[get_triage_client] = lambda: MockTriageClient(
        is_phishing=0.96, persuasion=Persuasion.AFFECTIVE_COERCION
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/scans",
                json={"content": "Oi mãe, troquei de número, me faz um pix urgente"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["threat_level"] == "GOLPE"
            assert "falso parente" in data["verdict_plain"].lower()
            assert data["details"]["channel"] == "texto"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_scan_url_only_returns_verdict():
    from scan_orchestrator.infrastructure.fakes import FakeRedisCacheClient
    from scan_orchestrator.api.dependencies import get_redis_client

    fake_redis = FakeRedisCacheClient()
    fake_redis.add_to_blacklist("https://banco-seguro-atualizacao.com.br")
    app.dependency_overrides[get_redis_client] = lambda: fake_redis
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/scans",
                json={"content": "https://banco-seguro-atualizacao.com.br"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["threat_level"] == "GOLPE"
            assert data["details"]["channel"] == "url"
            assert data["details"]["deciding_stage"] == "stage_0_blacklist_feed"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_scan_text_stream_sse():
    app.dependency_overrides[get_triage_client] = lambda: MockTriageClient(
        is_phishing=0.02, persuasion=Persuasion.NONE
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/scans/stream",
                json={"content": "Bom dia, lembre-se do nosso almoço às 12h."},
            )
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]
            body = resp.text
            assert "stage" in body
            assert "verdict" in body
            assert "SEGURO" in body
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_scan_image_returns_verdict():
    from contracts import ExtractResult
    from scan_orchestrator.infrastructure.image_extractor_client import FakeImageExtractorClient
    from scan_orchestrator.api.dependencies import get_image_extractor_client

    fake_extractor = FakeImageExtractorClient(
        default_result=ExtractResult(
            sha256="image_sha256",
            phash="phash_image",
            extracted_text="Aviso de cobrança urgente com PIX no CPF 000.000.000-00",
            qr_codes=[],
            urls_found=[],
        )
    )
    app.dependency_overrides[get_image_extractor_client] = lambda: fake_extractor
    app.dependency_overrides[get_triage_client] = lambda: MockTriageClient(
        is_phishing=0.94, persuasion=Persuasion.FINANCIAL_THREAT
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/scans",
                json={"image_b64": "fake_base64_screenshot_print"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["threat_level"] == "GOLPE"
            assert data["details"]["channel"] == "imagem"
            assert data["details"]["deciding_stage"] == "image_ocr_triage"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_scan_url_with_visual_rag_brand_spoofing():
    from contracts import InspectResult, BrandMatchResult
    from scan_orchestrator.infrastructure.fakes import FakeInspectorClient, FakeBrandMatcherClient
    from scan_orchestrator.api.dependencies import get_inspector_client, get_brand_matcher_client

    fake_inspector = FakeInspectorClient()
    target_url = "https://itau-seguranca-login.top/conta"
    fake_inspector.set_result(
        target_url,
        InspectResult(
            dom_text="Acesse sua conta",
            final_url=target_url,
            screenshot_b64="fake_screenshot_b64",
            is_blocked=False,
        ),
    )

    fake_brand = FakeBrandMatcherClient(
        default_result=BrandMatchResult(
            matched_brand="Itaú Unibanco",
            is_spoofing=True,
            similarity=0.96,
            official_domains=["itau.com.br"],
        )
    )

    app.dependency_overrides[get_inspector_client] = lambda: fake_inspector
    app.dependency_overrides[get_brand_matcher_client] = lambda: fake_brand
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/scans",
                json={"content": target_url},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["threat_level"] == "GOLPE"
            assert data["details"]["deciding_stage"] == "visual_rag_brand_spoofing"
            assert data["details"]["category"] == "brand_spoofing"
            assert data["details"]["scores"]["brand_spoofing"] == 1.0
            assert "imitação de marca" in data["verdict_plain"].lower()
    finally:
        app.dependency_overrides.clear()
