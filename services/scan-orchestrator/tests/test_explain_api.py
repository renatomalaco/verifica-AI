import json
from datetime import datetime
from uuid import uuid4

import httpx
import pytest
import respx
from httpx import ASGITransport, AsyncClient

from contracts import Channel, ExplainResult, ScanDetails, ScanResponse, ThreatLevel
from scan_orchestrator.api.dependencies import (
    get_explainer_client,
    get_quota_store,
    get_scan_repository,
    get_settings,
)
from scan_orchestrator.api.main import DEVICE_COOKIE, app
from scan_orchestrator.infrastructure.explainer_client import (
    FailingExplainerClient,
    FakeExplainerClient,
    HttpExplainerClient,
)
from scan_orchestrator.infrastructure.quota_store import InMemoryQuotaStore
from scan_orchestrator.infrastructure.scan_repository import InMemoryScanRepository
from scan_orchestrator.settings import Settings


def persisted_scan() -> ScanResponse:
    return ScanResponse(
        id=uuid4(),
        threat_level=ThreatLevel.SCAM,
        verdict_plain="Esta página imita um banco.",
        action_advice="Feche a página.",
        details=ScanDetails(
            channel=Channel.URL,
            deciding_stage="visual_rag_brand_spoofing",
            category="brand_spoofing",
            scores={"is_phishing": 1.0},
            domain_signals={"spoofed_brand": "Banco do Brasil"},
        ),
    )


@pytest.fixture
async def env():
    repo = InMemoryScanRepository()
    scan = persisted_scan()
    await repo.save("hash-do-conteudo", scan)
    explainer = FakeExplainerClient(ExplainResult(lines=["Linha 1", "Linha 2"]))
    store = InMemoryQuotaStore()
    settings = Settings(
        DEVICE_TOKEN_SECRET="segredo-de-teste",
        EXPLAIN_DAILY_LIMIT=2,
        EXPLAIN_MONTHLY_LIMIT=30,
        EXPLAIN_IP_LIMIT=100,
    )
    app.dependency_overrides[get_scan_repository] = lambda: repo
    app.dependency_overrides[get_explainer_client] = lambda: explainer
    app.dependency_overrides[get_quota_store] = lambda: store
    app.dependency_overrides[get_settings] = lambda: settings
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, scan, explainer, store
    app.dependency_overrides.clear()


async def test_explain_returns_lines_and_remaining_and_sets_device_cookie(env):
    client, scan, explainer, _ = env

    resp = await client.post(f"/api/v1/scans/{scan.id}/explain")

    assert resp.status_code == 200
    assert resp.json() == {"lines": ["Linha 1", "Linha 2"], "remaining_today": 1}
    set_cookie = resp.headers["set-cookie"]
    assert set_cookie.startswith(f"{DEVICE_COOKIE}=")
    assert "httponly" in set_cookie.lower()
    assert "samesite=lax" in set_cookie.lower()
    # The ai-gateway receives only the persisted verdict.
    assert explainer.requests[0].category == "brand_spoofing"
    assert explainer.requests[0].domain_signals == {"spoofed_brand": "Banco do Brasil"}


async def test_same_device_counts_down_and_gets_429_with_retry_at(env):
    client, scan, _, _ = env

    first = await client.post(f"/api/v1/scans/{scan.id}/explain")
    second = await client.post(f"/api/v1/scans/{scan.id}/explain")
    third = await client.post(f"/api/v1/scans/{scan.id}/explain")

    assert first.json()["remaining_today"] == 1
    assert second.json()["remaining_today"] == 0
    assert third.status_code == 429
    body = third.json()
    assert set(body) == {"retry_at"}
    assert datetime.fromisoformat(body["retry_at"]).tzinfo is not None


async def test_quota_never_blocks_the_verdict(env):
    client, scan, _, _ = env
    from scan_orchestrator.api.dependencies import get_triage_client
    from scan_orchestrator.infrastructure.fakes import FakeTriageClient

    app.dependency_overrides[get_triage_client] = lambda: FakeTriageClient()
    for _ in range(3):
        await client.post(f"/api/v1/scans/{scan.id}/explain")

    resp = await client.post("/api/v1/scans", json={"content": "Bom dia, tudo bem com você?"})
    assert resp.status_code == 200
    assert resp.json()["verdict_plain"]
    assert resp.json()["action_advice"]


async def test_tampered_cookie_is_replaced_by_a_new_device(env):
    client, scan, _, store = env
    client.cookies.set(DEVICE_COOKIE, "00000000-0000-0000-0000-000000000000.assinatura-falsa")

    resp = await client.post(f"/api/v1/scans/{scan.id}/explain")

    assert resp.status_code == 200
    assert "00000000-0000-0000-0000-000000000000" not in resp.headers["set-cookie"]
    assert not any("00000000-0000-0000-0000-000000000000" in k for k in store.counters)


async def test_unknown_scan_returns_404_without_consuming_quota(env):
    client, _, explainer, store = env

    resp = await client.post(f"/api/v1/scans/{uuid4()}/explain")

    assert resp.status_code == 404
    assert explainer.requests == []
    assert all(v == 0 for v in store.counters.values())


async def test_gateway_failure_returns_503_and_refunds_quota(env):
    client, scan, _, store = env
    app.dependency_overrides[get_explainer_client] = lambda: FailingExplainerClient()

    resp = await client.post(f"/api/v1/scans/{scan.id}/explain")

    assert resp.status_code == 503
    assert all(v == 0 for v in store.counters.values())


async def test_invalid_scan_id_is_rejected(env):
    client, _, _, _ = env
    resp = await client.post("/api/v1/scans/nao-e-uuid/explain")
    assert resp.status_code == 422


# --- ai-gateway HTTP client ---

async def test_http_explainer_posts_only_the_verdict_to_gateway():
    from scan_orchestrator.application.explain_scan import to_explain_request

    client = HttpExplainerClient(base_url="http://gateway.test")
    async with respx.mock(base_url="http://gateway.test") as mock:
        route = mock.post("/v1/explain").respond(json={"lines": ["ok"]})
        result = await client.explain(to_explain_request(persisted_scan()))

    assert result.lines == ["ok"]
    sent = json.loads(route.calls.last.request.content)
    assert sent["threat_level"] == "GOLPE"
    assert "content" not in sent


@pytest.mark.parametrize(
    "reply",
    [httpx.Response(502), httpx.Response(200, json={"lines": []}), httpx.ConnectError("fora")],
)
async def test_http_explainer_raises_runtime_error_on_failure(reply):
    from scan_orchestrator.application.explain_scan import to_explain_request

    client = HttpExplainerClient(base_url="http://gateway.test")
    async with respx.mock(base_url="http://gateway.test") as mock:
        route = mock.post("/v1/explain")
        if isinstance(reply, Exception):
            route.mock(side_effect=reply)
        else:
            route.mock(return_value=reply)
        with pytest.raises(RuntimeError):
            await client.explain(to_explain_request(persisted_scan()))
