from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

SERVICE_DIR = Path(__file__).resolve().parents[1]


def _config() -> Config:
    config = Config(str(SERVICE_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(SERVICE_DIR / "migrations"))
    return config


def test_migrations_form_a_single_line_of_history():
    # Two heads would make "alembic upgrade head" fail at deploy time.
    assert len(ScriptDirectory.from_config(_config()).get_heads()) == 1


def test_every_migration_renders_to_sql_without_a_database(monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@db.invalid/verifica_db")

    command.upgrade(_config(), "head", sql=True)

    sql = capsys.readouterr().out
    assert "CREATE TABLE analises_phishing" in sql
    assert "verdict_message" in sql
