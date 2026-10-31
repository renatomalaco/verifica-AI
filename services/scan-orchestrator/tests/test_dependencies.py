from scan_orchestrator.api.dependencies import get_brand_matcher_client, get_scan_repository
from scan_orchestrator.infrastructure.brand_matcher_client import HttpBrandMatcherClient
from scan_orchestrator.infrastructure.scan_repository import InMemoryScanRepository, SqlScanRepository
from scan_orchestrator.settings import Settings


def test_without_database_url_scans_stay_in_memory():
    assert isinstance(get_scan_repository(Settings(DATABASE_URL="")), InMemoryScanRepository)


def test_with_database_url_scans_are_persisted_in_sql():
    # Building the engine does not connect, so no database is needed here.
    settings = Settings(DATABASE_URL="postgresql+asyncpg://verifica:x@localhost:5432/verifica_db")
    assert isinstance(get_scan_repository(settings), SqlScanRepository)


def test_visual_rag_is_off_until_explicitly_enabled():
    # An unseeded catalog answers 503, which would cap every page at CUIDADO; off means "not run".
    assert Settings(_env_file=None).VISUAL_RAG_ENABLED is False
    assert get_brand_matcher_client(Settings(_env_file=None)) is None


def test_enabled_visual_rag_calls_the_ai_gateway():
    client = get_brand_matcher_client(Settings(_env_file=None, VISUAL_RAG_ENABLED=True))
    assert isinstance(client, HttpBrandMatcherClient)
