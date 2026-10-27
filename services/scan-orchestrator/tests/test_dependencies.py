from scan_orchestrator.api.dependencies import get_scan_repository
from scan_orchestrator.infrastructure.scan_repository import InMemoryScanRepository, SqlScanRepository
from scan_orchestrator.settings import Settings


def test_without_database_url_scans_stay_in_memory():
    assert isinstance(get_scan_repository(Settings(DATABASE_URL="")), InMemoryScanRepository)


def test_with_database_url_scans_are_persisted_in_sql():
    # Building the engine does not connect, so no database is needed here.
    settings = Settings(DATABASE_URL="postgresql+asyncpg://verifica:x@localhost:5432/verifica_db")
    assert isinstance(get_scan_repository(settings), SqlScanRepository)
