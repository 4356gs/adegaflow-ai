from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from app.db.session import create_database_engine
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError


def test_quote_artifact_migration_constraints_and_downgrade(
    tmp_path: Path,
) -> None:
    api_root = Path(__file__).resolve().parents[1]
    database_url = f"sqlite:///{tmp_path / 'quote-artifacts.db'}"
    config = Config(str(api_root / "alembic.ini"))
    config.attributes["database_url"] = database_url
    command.upgrade(config, "head")

    engine = create_database_engine(database_url)
    inspector = inspect(engine)
    assert {"quotes", "quote_items", "generated_artifacts"} <= set(
        inspector.get_table_names()
    )
    assert {item["name"] for item in inspector.get_unique_constraints("quotes")} == {
        "uq_quotes_agent_run_id"
    }
    assert {
        item["name"] for item in inspector.get_unique_constraints("quote_items")
    } == {"uq_quote_items_quote_product"}
    assert {
        item["name"]
        for item in inspector.get_unique_constraints("generated_artifacts")
    } == {"uq_generated_artifacts_run_type"}
    assert {fk["referred_table"] for fk in inspector.get_foreign_keys("quote_items")} == {
        "products",
        "quotes",
    }
    assert {
        check["name"] for check in inspector.get_check_constraints("quote_items")
    } >= {
        "ck_quote_items_line_total_exact",
        "ck_quote_items_quantity_positive",
    }
    with engine.connect() as connection:
        assert connection.scalar(text("PRAGMA foreign_keys")) == 1
        with pytest.raises(IntegrityError):
            connection.execute(
                text(
                    "INSERT INTO quotes "
                    "(id, agent_run_id, currency, subtotal_cents, status, assumptions, created_at) "
                    "VALUES ('q', 'missing', 'EUR', 0, 'draft', '{}', CURRENT_TIMESTAMP)"
                )
            )
    engine.dispose()

    command.downgrade(config, "0002_agent_run_traceability")
    engine = create_database_engine(database_url)
    tables = set(inspect(engine).get_table_names())
    assert "quotes" not in tables
    assert "quote_items" not in tables
    assert "generated_artifacts" not in tables
    assert "agent_runs" in tables
    engine.dispose()
