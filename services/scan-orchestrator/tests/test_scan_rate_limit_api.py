from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient
from redis.exceptions import ConnectionError as RedisConnectionError

from contracts import Persuasion, TriageResult
from scan_orchestrator.api.dependencies import get_quota_store, get_settings, get_triage_client
from scan_orchestrator.api.main import app
from scan_orchestrator.infrastructure.quota_store import InMemoryQuotaStore
from scan_orchestrator.settings import Settings

SCAM_TEXT = {"content": "Oi mãe, troquei de número, me faz um pix urgente"}


class SafeTriage:
    async def triage(self, text: str) -> TriageResult:
        return TriageResult(
            is_phishing=0.02, requires_visual_inspection=0.0, persuasion=Persuasion.NONE
        )


class BrokenStore(InMemoryQuotaStore):
    async def window_add(self, key, member, now, window_seconds):
        raise RedisConnectionError("redis is down")


@pytest.fixture
def one_scan_per_minute():
    settings = Settings(_env_file=None, SCAN_IP_LIMIT=1, SCAN_IP_WINDOW_SECONDS=60)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_triage_client] = SafeTriage
    store = InMemoryQuotaStore()
    app.dependency_overrides[get_quota_store] = lambda: store
    yield store
    app.dependency_overrides.clear()


def client_from(ip: str) -> AsyncClient:
    transport = ASGITransport(app=app, client=(ip, 50000))
    return AsyncClient(transport=transport, base_url="http://test")


async def test_second_scan_in_the_window_gets_a_code_and_when_to_retry(one_scan_per_minute):
    async with client_from("200.1.1.1") as client:
        first = await client.post("/api/v1/scans", json=SCAM_TEXT)
        second = await client.post("/api/v1/scans", json=SCAM_TEXT)

    assert first.status_code == 200
    assert second.status_code == 429
    body = second.json()
    assert body["code"] == "scan_rate_limited"
    assert datetime.fromisoformat(body["retry_at"])
    assert 1 <= int(second.headers["Retry-After"]) <= 60


async def test_stream_endpoint_shares_the_same_limit(one_scan_per_minute):
    async with client_from("200.1.1.1") as client:
        await client.post("/api/v1/scans", json=SCAM_TEXT)
        resp = await client.post("/api/v1/scans/stream", json=SCAM_TEXT)

    assert resp.status_code == 429
    assert resp.json()["code"] == "scan_rate_limited"


async def test_other_ips_are_not_affected(one_scan_per_minute):
    async with client_from("200.1.1.1") as client:
        await client.post("/api/v1/scans", json=SCAM_TEXT)
    async with client_from("200.2.2.2") as client:
        resp = await client.post("/api/v1/scans", json=SCAM_TEXT)

    assert resp.status_code == 200


async def test_scan_still_answers_when_the_limit_store_is_down(one_scan_per_minute):
    app.dependency_overrides[get_quota_store] = BrokenStore

    async with client_from("200.1.1.1") as client:
        first = await client.post("/api/v1/scans", json=SCAM_TEXT)
        second = await client.post("/api/v1/scans", json=SCAM_TEXT)

    assert (first.status_code, second.status_code) == (200, 200)
