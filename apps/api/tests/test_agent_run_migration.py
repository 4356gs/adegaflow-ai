from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_agent_run_migration_upgrades_and_downgrades(
    tmp_path: Path,
) -> None:
    api_root = Path(__file__).resolve().parents[1]
    database_path = tmp_path / "agent-run-migration.db"
    database_url = f"sqlite:///{database_path}"
    config = Config(str(api_root / "alembic.ini"))
    config.attributes["database_url"] = database_url

    command.upgrade(config, "head")
    engine = create_engine(database_url)
    tables = set(inspect(engine).get_table_names())
    assert {
        "agent_runs",
        "agent_run_events",
        "tool_executions",
    } <= tables
    engine.dispose()

    command.downgrade(config, "0001_catalog_customer_history")
    engine = create_engine(database_url)
    tables = set(inspect(engine).get_table_names())
    assert "agent_runs" not in tables
    assert "agent_run_events" not in tables
    assert "tool_executions" not in tables
    assert "inquiries" in tables
    assert "products" in tables
    engine.dispose()
