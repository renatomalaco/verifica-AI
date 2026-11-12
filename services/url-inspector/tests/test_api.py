import pytest
from httpx import AsyncClient, ASGITransport
from contracts import InspectRequest, InspectResult
from url_inspector.api.main import app, get_browser_driver
from url_inspector.infrastructure.fakes import FakeBrowserDriver


@pytest.fixture
def fake_driver():
    driver = FakeBrowserDriver()
    return driver


@pytest.fixture
def client(fake_driver):
    app.dependency_overrides[get_browser_driver] = lambda: fake_driver
    transport = ASGITransport(app=app)
    yield AsyncClient(transport=transport, base_url="http://test")
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "url-inspector"}


@pytest.mark.asyncio
async def test_inspect_url_success(client, fake_driver):
    fake_driver.set_result(
        "https://exemplo-promo.com",
        InspectResult(
            dom_text="Super Promoção de Celulares!",
            final_url="https://exemplo-promo.com",
            has_password_field=False,
            is_blocked=False,
        ),
    )

    payload = InspectRequest(url="https://exemplo-promo.com")
    response = await client.post("/inspect", json=payload.model_dump())

    assert response.status_code == 200
    data = response.json()
    assert data["dom_text"] == "Super Promoção de Celulares!"
    assert data["is_blocked"] is False
    assert data["has_password_field"] is False


@pytest.mark.asyncio
async def test_inspect_url_blocks_ssrf(client):
    payload = InspectRequest(url="http://169.254.169.254/latest/meta-data/")
    response = await client.post("/inspect", json=payload.model_dump())

    assert response.status_code == 400
    assert "SSRF" in response.json()["detail"]


@pytest.mark.asyncio
async def test_inspect_url_returns_blocked_when_antibot_triggered(client, fake_driver):
    fake_driver.set_result(
        "https://site-protegido.com",
        InspectResult(
            dom_text="",
            final_url="https://site-protegido.com",
            is_blocked=True,
            blocked_reason="cloudflare_challenge",
        ),
    )

    payload = InspectRequest(url="https://site-protegido.com")
    response = await client.post("/inspect", json=payload.model_dump())

    assert response.status_code == 200
    data = response.json()
    assert data["is_blocked"] is True
    assert data["blocked_reason"] == "cloudflare_challenge"


class BrokenDriver:
    async def inspect(self, url: str, timeout_seconds: float = 6.0) -> InspectResult:
        raise TimeoutError("navigation timed out")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url", ["file:///etc/passwd", "javascript:alert(1)", "ftp://exemplo.com/arquivo"]
)
async def test_inspect_refuses_schemes_other_than_http(client, url):
    response = await client.post("/inspect", json={"url": url})

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_inspect_refuses_a_url_without_host(client):
    response = await client.post("/inspect", json={"url": "https:///caminho"})

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_a_browser_failure_comes_back_blocked_never_as_a_clean_page(client):
    app.dependency_overrides[get_browser_driver] = BrokenDriver

    response = await client.post("/inspect", json={"url": "https://lento.example"})

    assert response.status_code == 200
    data = response.json()
    assert data["is_blocked"] is True
    assert data["blocked_reason"].startswith("inspection_error")
