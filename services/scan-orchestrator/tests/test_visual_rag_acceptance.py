"""R4 acceptance: a page with a bank's look on an unofficial domain is GOLPE (brand_spoofing)
without asking the VLM. Orchestrator cascade -> ai-gateway (in process) -> real pgvector."""
import base64
import io
import os

import httpx
import pytest
from PIL import Image, ImageDraw
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from ai_gateway.api.main import app as gateway_app, get_brand_catalog, get_brand_verifier, get_visual_embedder
from ai_gateway.infrastructure.fakes import FakeBrandVerifier, FakeVisualEmbedder, one_hot
from ai_gateway.infrastructure.pgvector_catalog import PgvectorBrandCatalog
from contracts import InspectResult, ThreatLevel
from scan_orchestrator.domain.cascade import Cascade, Stage2RemoteInspection, StageContext
from scan_orchestrator.domain.decision import ThresholdPolicy
from scan_orchestrator.infrastructure.brand_matcher_client import HttpBrandMatcherClient
from scan_orchestrator.infrastructure.fakes import FakeInspectorClient, FakeTriageClient

pytestmark = pytest.mark.integration

DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")
SOURCE = "teste-r4/aceite.png"
PHISHING_URL = "https://bb-atualizacao-cadastral.top/entrar"


def _bank_login_page(image_format: str, quality: int = 95) -> str:
    """A crude bank-like login page: yellow header, blue logo block, two input boxes."""
    page = Image.new("RGB", (800, 600), (255, 255, 255))
    draw = ImageDraw.Draw(page)
    draw.rectangle((0, 0, 800, 110), fill=(252, 236, 0))
    draw.rectangle((30, 20, 150, 90), fill=(0, 56, 168))
    for top in (220, 300):
        draw.rectangle((250, top, 550, top + 50), outline=(120, 120, 120), width=3)
    buffer = io.BytesIO()
    page.save(buffer, format=image_format, quality=quality)
    return base64.b64encode(buffer.getvalue()).decode()


def _siglip():
    pytest.importorskip("transformers", reason="install the ai-gateway 'siglip' extra")
    from ai_gateway.infrastructure.siglip_embedder import SiglipEmbedder

    return SiglipEmbedder(model_name="google/siglip-base-patch16-224", dimension=768)


EMBEDDERS = {
    "fake": lambda: FakeVisualEmbedder(default_embedding=one_hot(3, 768)),
    "siglip": _siglip,
}


@pytest.fixture
async def catalog():
    if not DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set (needs the migrated Postgres from infra/docker-compose.yml)")
    engine = create_async_engine(DATABASE_URL)
    yield PgvectorBrandCatalog(engine)
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM marcas_referencias WHERE source = :source"), {"source": SOURCE})
    await engine.dispose()
    gateway_app.dependency_overrides.clear()


@pytest.mark.parametrize("embedder_name", sorted(EMBEDDERS))
async def test_bank_look_on_an_unofficial_domain_is_scam_without_the_vlm(catalog, embedder_name):
    embedder = EMBEDDERS[embedder_name]()
    await catalog.save_reference("Banco do Brasil", SOURCE, await embedder.embed_image(_bank_login_page("PNG")))
    verifier = FakeBrandVerifier(answer=True)
    gateway_app.dependency_overrides[get_visual_embedder] = lambda: embedder
    gateway_app.dependency_overrides[get_brand_catalog] = lambda: catalog
    gateway_app.dependency_overrides[get_brand_verifier] = lambda: verifier

    inspector = FakeInspectorClient()
    # What reaches the matcher is a recompressed screenshot, not the reference file itself.
    inspector.set_result(
        PHISHING_URL,
        InspectResult(final_url=PHISHING_URL, dom_text="Acesse sua conta", screenshot_b64=_bank_login_page("JPEG", 60)),
    )
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=gateway_app)) as http:
        stage2 = Stage2RemoteInspection(
            inspector_client=inspector,
            triage_client=FakeTriageClient(),
            brand_matcher=HttpBrandMatcherClient(base_url="http://ai-gateway", client=http),
        )
        policy = ThresholdPolicy(scam=0.90, safe=0.10)
        result = await Cascade(stages=[stage2], policy=policy).run(StageContext(raw_url=PHISHING_URL))

    assert result.threat_level is ThreatLevel.SCAM
    assert result.details.category == "brand_spoofing"
    assert result.details.deciding_stage == "visual_rag_brand_spoofing"
    assert result.details.domain_signals["spoofed_brand"] == "Banco do Brasil"
    assert verifier.calls == 0
