import pytest
from httpx import AsyncClient, ASGITransport
from research_runner.api.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["service"] == "research-runner"


@pytest.mark.asyncio
async def test_get_pesquisa_summary():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/pesquisa")
        assert res.status_code == 200
        data = res.json()
        assert "markdown_table" in data
        assert "latex_table" in data
        assert "evaluations" in data
        assert len(data["evaluations"]) == 4


@pytest.mark.asyncio
async def test_post_pesquisa_run_mode():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/pesquisa/run?mode=cascade")
        assert res.status_code == 200
        data = res.json()
        assert data["mode"] == "cascade"
        assert data["metrics"]["f1_score"] >= 0.92
