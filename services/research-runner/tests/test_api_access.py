from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from contracts import ResearchRole
from research_runner.api import main
from research_runner.api.main import app
from scan_orchestrator.api.dependencies import get_settings
from scan_orchestrator.api.research_guard import ACCESS_COOKIE
from scan_orchestrator.infrastructure.access_tokens import AccessTokenIssuer, generate_key_pair
from scan_orchestrator.settings import Settings

PRIVATE_KEY, PUBLIC_KEY = generate_key_pair()
ORIGIN = "https://verifica.test"
REPORT = {"modes": [], "dataset_size": 0}


@pytest.fixture
async def client(monkeypatch, tmp_path):
    # The research-runner only verifies tokens: it never receives the private key.
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, AUTH_JWT_PUBLIC_KEY=PUBLIC_KEY, AUTH_ALLOWED_ORIGINS=[ORIGIN]
    )
    monkeypatch.setattr(main, "reports_dir", lambda: tmp_path)
    monkeypatch.setattr(main, "load_samples", lambda: [])

    async def fake_study(samples, config):
        return REPORT

    monkeypatch.setattr(main, "run_study", fake_study)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test", headers={"Origin": ORIGIN}) as http:
        yield http
    app.dependency_overrides.pop(get_settings, None)


def sign_in(client: AsyncClient, role: ResearchRole) -> None:
    client.cookies.set(ACCESS_COOKIE, AccessTokenIssuer(PRIVATE_KEY).issue(uuid4(), role))


async def test_without_login_the_research_area_answers_401(client):
    assert (await client.get("/pesquisa/report")).status_code == 401
    assert (await client.post("/pesquisa/run")).status_code == 401


async def test_a_researcher_reads_the_report_but_cannot_run_the_study(client):
    sign_in(client, ResearchRole.RESEARCHER)

    assert (await client.get("/pesquisa/report")).status_code == 404  # signed in; no study run yet
    assert (await client.post("/pesquisa/run")).status_code == 403


async def test_the_admin_runs_the_study_and_then_reads_it(client):
    sign_in(client, ResearchRole.ADMIN)

    assert (await client.post("/pesquisa/run")).status_code == 200
    assert (await client.get("/pesquisa/report")).status_code == 200


async def test_running_the_study_from_another_origin_is_refused(client):
    sign_in(client, ResearchRole.ADMIN)

    res = await client.post("/pesquisa/run", headers={"Origin": "https://site-malicioso.test"})

    assert res.status_code == 403


async def test_a_token_from_another_issuer_is_refused(client):
    other_private, _ = generate_key_pair()
    client.cookies.set(ACCESS_COOKIE, AccessTokenIssuer(other_private).issue(uuid4(), ResearchRole.ADMIN))

    assert (await client.get("/pesquisa/report")).status_code == 401
