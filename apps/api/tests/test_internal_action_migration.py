from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from app.db.session import create_database_engine
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError


def test_internal_action_migration_is_constrained_and_reversible(
    tmp_path: Path,
) -> None:
    api_root = Path(__file__).resolve().parents[1]
    database_url = f"sqlite:///{tmp_path / 'internal-actions.db'}"
    config = Config(str(api_root / "alembic.ini"))
    config.attributes["database_url"] = database_url
    command.upgrade(config, "head")

    engine = create_database_engine(database_url)
    inspector = inspect(engine)
    assert {"follow_up_tasks", "internal_action_receipts"} <= set(inspector.get_table_names())
    assert {
        item["name"] for item in inspector.get_unique_constraints("internal_action_receipts")
    } == {
        "uq_internal_action_receipts_idempotency_key",
        "uq_internal_action_receipts_run_action",
    }
    assert {fk["referred_table"] for fk in inspector.get_foreign_keys("follow_up_tasks")} == {
        "opportunities"
    }
    assert {
        fk["referred_table"] for fk in inspector.get_foreign_keys("internal_action_receipts")
    } == {"agent_runs"}
    with engine.connect() as connection:
        assert connection.scalar(text("PRAGMA foreign_keys")) == 1
        with pytest.raises(IntegrityError):
            connection.execute(
                text(
                    "INSERT INTO internal_action_receipts "
                    "(id, agent_run_id, action_name, idempotency_key, "
                    "request_fingerprint, result_payload, created_at) VALUES "
                    "('r', 'missing', 'create_crm_opportunity', 'key', "
                    "'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', "
                    "'{}', CURRENT_TIMESTAMP)"
                )
            )
    engine.dispose()

    command.downgrade(config, "0003_quote_artifacts")
    engine = create_database_engine(database_url)
    tables = set(inspect(engine).get_table_names())
    assert "follow_up_tasks" not in tables
    assert "internal_action_receipts" not in tables
    assert "quotes" in tables
    engine.dispose()
