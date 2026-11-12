import pytest

from scan_orchestrator.api.dependencies import (
    get_domain_evidence_client,
    get_quota_store,
    get_settings,
)
from scan_orchestrator.api.main import app
from scan_orchestrator.infrastructure.fakes import FakeDomainEvidenceClient
from scan_orchestrator.infrastructure.quota_store import InMemoryQuotaStore
from scan_orchestrator.settings import Settings


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch):
    """Unit tests must not pick up the developer's .env (e.g. a DATABASE_URL pointing at
    a real Postgres)."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)
    # No network in unit tests: RDAP, crt.sh and Tranco answer "unknown".
    app.dependency_overrides[get_domain_evidence_client] = FakeDomainEvidenceClient
    # The scan flood guard counts in memory, fresh for each test.
    store = InMemoryQuotaStore()
    app.dependency_overrides[get_quota_store] = lambda: store
    yield
    app.dependency_overrides.pop(get_settings, None)
    app.dependency_overrides.pop(get_domain_evidence_client, None)
    app.dependency_overrides.pop(get_quota_store, None)
