import pytest

from scan_orchestrator.api.dependencies import get_settings
from scan_orchestrator.api.main import app
from scan_orchestrator.settings import Settings


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch):
    """Unit tests must not pick up the developer's .env (e.g. a DATABASE_URL pointing at a real Postgres)."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)
    yield
    app.dependency_overrides.pop(get_settings, None)
