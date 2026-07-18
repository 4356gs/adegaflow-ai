from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from app.db.session import create_database_engine
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError


def test_http_async_migration_is_reversible_and_enforces_keys(tmp_path: Path) -> None:
    api_root = Path(__file__).resolve().parents[1]
    database_url = f"sqlite:///{tmp_path / 'http-async.db'}"
    config = Config(str(api_root / "alembic.ini"))
    config.attributes["database_url"] = database_url

    command.upgrade(config, "0004_internal_actions")
    engine = create_database_engine(database_url)
    assert "submission_key" not in {
        item["name"] for item in inspect(engine).get_columns("inquiries")
    }
    engine.dispose()

    command.upgrade(config, "head")
    engine = create_database_engine(database_url)
    inspector = inspect(engine)
    inquiry_columns = {item["name"] for item in inspector.get_columns("inquiries")}
    run_columns = {item["name"] for item in inspector.get_columns("agent_runs")}
    assert "submission_key" in inquiry_columns
    assert {"request_key", "retry_of_run_id"} <= run_columns
    assert "uq_inquiries_submission_key" in {
        item["name"] for item in inspector.get_indexes("inquiries")
    }
    assert "uq_agent_runs_request_key" in {
        item["name"] for item in inspector.get_indexes("agent_runs")
    }
    assert any(
        item["referred_table"] == "agent_runs"
        and item["constrained_columns"] == ["retry_of_run_id"]
        for item in inspector.get_foreign_keys("agent_runs")
    )

    inquiry_values = {
        "id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1",
        "source": "manual",
        "raw_message": "hello",
        "status": "new",
        "extracted_data": "{}",
        "missing_fields": "[]",
        "received_at": "2026-07-18 12:00:00",
    }
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO inquiries "
                "(id, source, raw_message, status, extracted_data, missing_fields, received_at) "
                "VALUES (:id, :source, :raw_message, :status, :extracted_data, "
                ":missing_fields, :received_at)"
            ),
            inquiry_values,
        )
        second = dict(inquiry_values)
        second["id"] = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa2"
        connection.execute(
            text(
                "INSERT INTO inquiries "
                "(id, source, raw_message, status, extracted_data, missing_fields, received_at) "
                "VALUES (:id, :source, :raw_message, :status, :extracted_data, "
                ":missing_fields, :received_at)"
            ),
            second,
        )
        connection.execute(
            text("UPDATE inquiries SET submission_key='same-key' WHERE id=:id"),
            {"id": inquiry_values["id"]},
        )
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            text("UPDATE inquiries SET submission_key='same-key' WHERE id=:id"),
            {"id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa2"},
        )
    engine.dispose()

    command.downgrade(config, "0004_internal_actions")
    engine = create_database_engine(database_url)
    inspector = inspect(engine)
    assert "submission_key" not in {item["name"] for item in inspector.get_columns("inquiries")}
    assert not {"request_key", "retry_of_run_id"} & {
        item["name"] for item in inspector.get_columns("agent_runs")
    }
    engine.dispose()
