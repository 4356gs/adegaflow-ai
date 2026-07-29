"""Reproducible terminal demonstrations for Sprint 2 Block 9."""

from __future__ import annotations

import argparse
import json
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from app.api.dependencies import get_session
from app.core.config import Settings
from app.db.models import (
    CustomerMemory,
    FollowUpTask,
    InternalActionReceipt,
    Inventory,
    Opportunity,
)
from app.db.seed import load_seed_file, seed_demo_data
from app.db.session import create_database_engine
from app.main import app
from app.services.async_runs import LocalRunDispatcher
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from .test_backend_closeout_e2e import (
    CUSTOMER_ID,
    ClientSequence,
    _create_inquiry,
    _event_sequences,
    _poll,
    _start_run,
)

ROOT = Path(__file__).resolve().parents[3]


def _show(label: str, payload: object) -> None:
    print(f"\n{label}")
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))


def _counts(factory: sessionmaker[Session]) -> dict[str, int]:
    models = {
        "opportunities": Opportunity,
        "followups": FollowUpTask,
        "receipts": InternalActionReceipt,
        "memories": CustomerMemory,
    }
    with factory() as session:
        return {
            name: session.scalar(select(func.count()).select_from(model)) or 0
            for name, model in models.items()
        }


def _business_counts(
    factory: sessionmaker[Session],
    *,
    inquiry_id: str,
    run_id: str,
) -> dict[str, int]:
    with factory() as session:
        opportunity = session.scalar(
            select(Opportunity).where(Opportunity.inquiry_id == inquiry_id)
        )
        return {
            "opportunities": 1 if opportunity else 0,
            "followups": (
                session.scalar(
                    select(func.count())
                    .select_from(FollowUpTask)
                    .where(FollowUpTask.opportunity_id == opportunity.id)
                )
                if opportunity
                else 0
            )
            or 0,
            "receipts": session.scalar(
                select(func.count())
                .select_from(InternalActionReceipt)
                .where(InternalActionReceipt.agent_run_id == run_id)
            )
            or 0,
            "active_memories": session.scalar(
                select(func.count())
                .select_from(CustomerMemory)
                .where(
                    CustomerMemory.customer_id == CUSTOMER_ID,
                    CustomerMemory.is_active.is_(True),
                )
            )
            or 0,
        }


@contextmanager
def _environment(
    clients: ClientSequence,
) -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    with tempfile.TemporaryDirectory(prefix="adegaflow-block9-") as directory:
        database_path = Path(directory) / "demo.db"
        database_url = f"sqlite:///{database_path}"
        alembic = Config(str(ROOT / "apps/api/alembic.ini"))
        alembic.attributes["database_url"] = database_url
        command.upgrade(alembic, "head")

        engine = create_database_engine(database_url)
        factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
        with factory() as session:
            summary = seed_demo_data(
                session,
                load_seed_file(ROOT / "data/seeds/demo_seed.json"),
            )
            session.commit()
        _show(
            "1. Temporary database migrated and seeded",
            {
                "database": str(database_path),
                "alembic_head": "0005_http_async_runs",
                **summary.model_dump(),
            },
        )

        def override_session() -> Iterator[Session]:
            with factory() as session:
                yield session

        dispatcher = LocalRunDispatcher(
            session_factory=factory,
            settings=Settings(ASYNC_RUN_QUEUE_CAPACITY=10),
            client_factory=clients,
        )
        app.dependency_overrides[get_session] = override_session
        app.state.run_dispatcher = dispatcher
        try:
            with TestClient(app) as client:
                yield client, factory
        finally:
            app.dependency_overrides.clear()
            if hasattr(app.state, "run_dispatcher"):
                del app.state.run_dispatcher
            engine.dispose()


def run_happy() -> None:
    clients = ClientSequence()
    with _environment(clients) as (client, factory):
        with factory() as session:
            inventory_before = list(
                session.execute(
                    select(
                        Inventory.product_id,
                        Inventory.available_bottles,
                        Inventory.reserved_bottles,
                    ).order_by(Inventory.product_id)
                )
            )
        inquiry_id, created_status = _create_inquiry(client, "demo-inquiry-1")
        _show(
            "2. Inquiry command and equivalent replay",
            {"created_status": created_status, "replayed_status": 200, "inquiry_id": inquiry_id},
        )
        run_id = _start_run(client, inquiry_id, "demo-run-1")
        _show("3. Run accepted", {"status": 202, "agent_run_id": run_id})
        terminal = _poll(client, run_id)
        sequences = _event_sequences(client, run_id)
        _show(
            "4. Polling reached terminal state",
            {
                "status": terminal["status"],
                "event_count": len(sequences),
                "ordered_sequences": sequences,
            },
        )
        result = client.get(f"/api/v1/agent-runs/{run_id}/result").json()
        _show("5. Expanded authoritative result", result)
        opportunity_id = result["opportunity"]["id"]
        _show(
            "6. Opportunity read",
            client.get(f"/api/v1/opportunities/{opportunity_id}").json(),
        )
        _show(
            "7. Customer memory read",
            client.get(f"/api/v1/customers/{CUSTOMER_ID}/memory").json(),
        )
        first_counts = _business_counts(factory, inquiry_id=inquiry_id, run_id=run_id)
        _show("8. Commercial counts after first session", first_counts)
        assert first_counts == {
            "opportunities": 1,
            "followups": 1,
            "receipts": 3,
            "active_memories": 5,
        }

        inquiry_two, _ = _create_inquiry(client, "demo-inquiry-2")
        run_two = _start_run(client, inquiry_two, "demo-run-2")
        terminal_two = _poll(client, run_two)
        memory_input = clients.clients[1].request_messages[0][1]["content"]
        assert "Interested in Atlantic white wines" in memory_input
        assert "Old preference for mixed cases" not in memory_input
        _show(
            "9. Second session recovered active memory",
            {
                "inquiry_id": inquiry_two,
                "agent_run_id": run_two,
                "status": terminal_two["status"],
                "active_memory_recovered": True,
                "counts": _counts(factory),
            },
        )
        with factory() as session:
            inventory_after = list(
                session.execute(
                    select(
                        Inventory.product_id,
                        Inventory.available_bottles,
                        Inventory.reserved_bottles,
                    ).order_by(Inventory.product_id)
                )
            )
        assert inventory_after == inventory_before
        _show("10. Inventory remained unchanged", {"unchanged": True})


def run_retry() -> None:
    clients = ClientSequence([True, False])
    with _environment(clients) as (client, factory):
        inquiry_id, _ = _create_inquiry(client, "demo-retry-inquiry")
        original_id = _start_run(client, inquiry_id, "demo-retry-original")
        original = _poll(client, original_id)
        original_events = _event_sequences(client, original_id)
        _show(
            "2. Original run failed safely",
            {
                "agent_run_id": original_id,
                "status": original["status"],
                "error": original["error"],
                "retryable": original["retryable"],
            },
        )
        assert original["error"]["code"] == "QWEN_TIMEOUT"
        retry = client.post(
            f"/api/v1/agent-runs/{original_id}/retry",
            headers={"Idempotency-Key": "demo-retry-command"},
        )
        repeated = client.post(
            f"/api/v1/agent-runs/{original_id}/retry",
            headers={"Idempotency-Key": "demo-retry-command"},
        )
        assert retry.status_code == 202
        retry_id = retry.json()["agent_run_id"]
        assert repeated.json()["agent_run_id"] == retry_id
        terminal = _poll(client, retry_id)
        _show(
            "3. Retry created a new immutable run",
            {
                "status": retry.status_code,
                "agent_run_id": retry_id,
                "retry_of_run_id": retry.json()["retry_of_run_id"],
                "terminal_status": terminal["status"],
                "replay_same_resource": True,
            },
        )
        assert retry_id != original_id
        assert client.get(f"/api/v1/agent-runs/{original_id}").json() == original
        assert _event_sequences(client, original_id) == original_events
        failed_result = client.get(f"/api/v1/agent-runs/{original_id}/result").json()
        assert failed_result["opportunity"] is None
        assert failed_result["followup"] is None
        _show(
            "4. Original remained unchanged and owns no retry actions",
            {"immutable": True, "counts": _counts(factory)},
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", choices=("happy", "retry"))
    args = parser.parse_args()
    if args.scenario == "happy":
        run_happy()
    else:
        run_retry()


if __name__ == "__main__":
    main()
