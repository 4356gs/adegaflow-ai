from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from app.api.dependencies import get_session
from app.core.config import Settings
from app.db.base import Base
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

from .fake_qwen import FakeQwenClient

CUSTOMER_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1"
TERMINAL = {"needs_review", "completed", "failed"}
MESSAGE = (
    "We need 600 bottles of Albariño for specialised wine shops in Germany. "
    "Recommend two references."
)


class ClientSequence:
    def __init__(self, failures: list[bool] | None = None) -> None:
        self.failures = list(failures or [])
        self.clients: list[FakeQwenClient] = []

    def __call__(self, session: Session) -> FakeQwenClient:
        client = FakeQwenClient(
            session,
            fail_first_json=self.failures.pop(0) if self.failures else False,
        )
        self.clients.append(client)
        return client


@pytest.fixture
def full_stack(
    tmp_path: Path,
) -> Iterator[
    Callable[
        [ClientSequence],
        tuple[TestClient, sessionmaker[Session], LocalRunDispatcher],
    ]
]:
    active: list[tuple[TestClient, LocalRunDispatcher]] = []

    def build(
        clients: ClientSequence,
    ) -> tuple[TestClient, sessionmaker[Session], LocalRunDispatcher]:
        engine = create_database_engine(f"sqlite:///{tmp_path / 'closeout.db'}")
        Base.metadata.create_all(engine)
        factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
        seed_path = Path(__file__).resolve().parents[3] / "data/seeds/demo_seed.json"
        with factory() as session:
            seed_demo_data(session, load_seed_file(seed_path))
            session.commit()

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
        test_client = TestClient(app)
        test_client.__enter__()
        active.append((test_client, dispatcher))
        return test_client, factory, dispatcher

    yield build

    for client, _dispatcher in reversed(active):
        client.__exit__(None, None, None)
    app.dependency_overrides.clear()
    if hasattr(app.state, "run_dispatcher"):
        del app.state.run_dispatcher


def _create_inquiry(client: TestClient, key: str) -> tuple[str, int]:
    payload = {
        "source": "demo",
        "raw_message": MESSAGE,
        "customer_id": CUSTOMER_ID,
    }
    created = client.post(
        "/api/v1/inquiries",
        json=payload,
        headers={"Idempotency-Key": key},
    )
    repeated = client.post(
        "/api/v1/inquiries",
        json=payload,
        headers={"Idempotency-Key": key},
    )
    assert created.status_code == 201
    assert repeated.status_code == 200
    assert repeated.json()["id"] == created.json()["id"]
    return created.json()["id"], created.status_code


def _start_run(client: TestClient, inquiry_id: str, key: str) -> str:
    path = f"/api/v1/inquiries/{inquiry_id}/agent-runs"
    accepted = client.post(path, headers={"Idempotency-Key": key})
    repeated = client.post(path, headers={"Idempotency-Key": key})
    assert accepted.status_code == 202
    assert repeated.status_code == 202
    assert repeated.json()["agent_run_id"] == accepted.json()["agent_run_id"]
    return accepted.json()["agent_run_id"]


def _poll(client: TestClient, run_id: str, *, timeout: float = 8.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"/api/v1/agent-runs/{run_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] in TERMINAL:
            return payload
        time.sleep(0.01)
    raise AssertionError(f"Run {run_id} did not become terminal within {timeout} seconds.")


def _event_sequences(client: TestClient, run_id: str) -> list[int]:
    cursor = 0
    sequences: list[int] = []
    while True:
        response = client.get(
            f"/api/v1/agent-runs/{run_id}/events",
            params={"after_sequence": cursor, "limit": 7},
        )
        assert response.status_code == 200
        payload = response.json()
        batch = [item["sequence"] for item in payload["events"]]
        sequences.extend(batch)
        if batch:
            cursor = batch[-1]
        if payload["terminal"] and not batch:
            break
    return sequences


def _count(factory: sessionmaker[Session], model: type[Any]) -> int:
    with factory() as session:
        return session.scalar(select(func.count()).select_from(model)) or 0


def test_http_dispatcher_happy_path_idempotency_and_second_session(
    full_stack: Callable[
        [ClientSequence],
        tuple[TestClient, sessionmaker[Session], LocalRunDispatcher],
    ],
) -> None:
    clients = ClientSequence()
    client, factory, dispatcher = full_stack(clients)
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

    inquiry_id, _ = _create_inquiry(client, "e2e-inquiry-1")
    run_id = _start_run(client, inquiry_id, "e2e-run-1")
    terminal = _poll(client, run_id)
    assert terminal["status"] == "needs_review"
    assert dispatcher._consumer is not None

    sequences = _event_sequences(client, run_id)
    assert sequences == list(range(1, len(sequences) + 1))
    result = client.get(f"/api/v1/agent-runs/{run_id}/result")
    assert result.status_code == 200
    body = result.json()
    assert body["analysis"]["market"] == "DE"
    assert body["recommendation"]["total_bottles"] == 600
    assert body["quote"]["subtotal_cents"] == 609000
    assert {item["artifact_type"] for item in body["artifacts"]} == {
        "proposal",
        "email_draft",
    }
    assert body["opportunity"]["id"] == terminal["references"]["opportunity_id"]
    assert body["followup"]["id"] == terminal["references"]["followup_task_id"]

    second_inquiry_id, _ = _create_inquiry(client, "e2e-inquiry-2")
    second_run_id = _start_run(client, second_inquiry_id, "e2e-run-2")
    assert _poll(client, second_run_id)["status"] == "needs_review"
    second_model_input = clients.clients[1].request_messages[0][1]["content"]
    assert "Interested in Atlantic white wines" in second_model_input
    assert "Old preference for mixed cases" not in second_model_input

    memory = client.get(f"/api/v1/customers/{CUSTOMER_ID}/memory")
    assert memory.status_code == 200
    assert len(memory.json()["items"]) == 8
    assert _count(factory, Opportunity) == 3
    assert _count(factory, FollowUpTask) == 2
    assert _count(factory, InternalActionReceipt) == 6
    assert _count(factory, CustomerMemory) == 10
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


def test_http_retry_creates_new_run_and_keeps_original_immutable(
    full_stack: Callable[
        [ClientSequence],
        tuple[TestClient, sessionmaker[Session], LocalRunDispatcher],
    ],
) -> None:
    clients = ClientSequence([True, False])
    client, factory, _ = full_stack(clients)
    inquiry_id, _ = _create_inquiry(client, "retry-inquiry")
    original_id = _start_run(client, inquiry_id, "retry-original")
    original = _poll(client, original_id)
    original_events = _event_sequences(client, original_id)

    assert original["status"] == "failed"
    assert original["error"]["code"] == "QWEN_TIMEOUT"
    assert original["retryable"] is True
    response = client.post(
        f"/api/v1/agent-runs/{original_id}/retry",
        headers={"Idempotency-Key": "retry-command"},
    )
    repeated = client.post(
        f"/api/v1/agent-runs/{original_id}/retry",
        headers={"Idempotency-Key": "retry-command"},
    )
    assert response.status_code == 202
    retry_id = response.json()["agent_run_id"]
    assert retry_id != original_id
    assert response.json()["retry_of_run_id"] == original_id
    assert repeated.json()["agent_run_id"] == retry_id
    assert _poll(client, retry_id)["status"] == "needs_review"

    unchanged = client.get(f"/api/v1/agent-runs/{original_id}").json()
    assert unchanged == original
    assert _event_sequences(client, original_id) == original_events
    failed_result = client.get(f"/api/v1/agent-runs/{original_id}/result").json()
    assert failed_result["opportunity"] is None
    assert failed_result["followup"] is None
    assert _count(factory, Opportunity) == 2
    assert _count(factory, FollowUpTask) == 1
    assert _count(factory, InternalActionReceipt) == 3
