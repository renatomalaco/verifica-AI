import io
import base64
import pytest
from httpx import AsyncClient, ASGITransport
from PIL import Image
from image_extractor.api.main import app, get_extractor_service
from image_extractor.domain.extractor_service import ImageExtractorService
from image_extractor.domain.ocr_reader import FakeOcrEngine, FakeQrReader


def create_sample_image() -> str:
    img = Image.new("RGB", (50, 50), color="green")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


@pytest.fixture
def fake_service():
    ocr = FakeOcrEngine(text="Texto de teste da imagem com link https://site-fake.top")
    qr = FakeQrReader(qr_codes=[])
    return ImageExtractorService(ocr_engine=ocr, qr_reader=qr)


@pytest.fixture
def client(fake_service):
    app.dependency_overrides[get_extractor_service] = lambda: fake_service
    transport = ASGITransport(app=app)
    yield AsyncClient(transport=transport, base_url="http://test")
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "image-extractor"}


@pytest.mark.asyncio
async def test_extract_endpoint_success(client):
    b64 = create_sample_image()
    response = await client.post("/extract", json={"image_b64": b64})
    assert response.status_code == 200
    data = response.json()
    assert "https://site-fake.top" in data["urls_found"]
    assert len(data["sha256"]) == 64
    assert len(data["phash"]) == 16


@pytest.mark.asyncio
async def test_extract_endpoint_invalid_image(client):
    response = await client.post("/extract", json={"image_b64": "invalid_junk"})
    assert response.status_code == 400
    assert "invalid" in response.json()["detail"].lower()
