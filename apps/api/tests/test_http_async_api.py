from collections.abc import Iterator
from pathlib import Path

import pytest
from app.api.dependencies import get_session
from app.db.base import Base
from app.db.models import AgentRun
from app.db.seed import load_seed_file, seed_demo_data
from app.db.session import create_database_engine
from app.domain.enums import AgentRunStep
from app.main import app
from app.repositories.agent_runs import AgentRunRepository
from app.services.async_runs import QueueFullError
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

INQUIRY_ID = "dddddddd-dddd-4ddd-8ddd-ddddddddddd1"


class FakeDispatcher:
    def __init__(self) -> None:
        self.enqueued: list[str] = []
        self.reject = False

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    def enqueue(self, run_id: str) -> None:
        if self.reject:
            raise QueueFullError
        self.enqueued.append(run_id)


@pytest.fixture
def api_client(
    tmp_path: Path,
) -> Iterator[tuple[TestClient, FakeDispatcher, Session]]:
    dispatcher = FakeDispatcher()
    engine = create_database_engine(f"sqlite:///{tmp_path / 'api.db'}")
    Base.metadata.create_all(engine)
    seed_path = Path(__file__).resolve().parents[3] / "data/seeds/demo_seed.json"
    with Session(engine, expire_on_commit=False) as session:
        seed_demo_data(session, load_seed_file(seed_path))
        session.commit()

        def override_session() -> Iterator[Session]:
            yield session

        app.dependency_overrides[get_session] = override_session
        app.state.run_dispatcher = dispatcher
        with TestClient(app) as client:
            yield client, dispatcher, session
        app.dependency_overrides.clear()
        del app.state.run_dispatcher
    engine.dispose()


def test_inquiry_create_is_idempotent_and_versioned(
    api_client: tuple[TestClient, FakeDispatcher, Session],
) -> None:
    client, _, _ = api_client
    payload = {"source": "manual", "raw_message": "  Need 120 bottles.  "}
    headers = {"Idempotency-Key": "inquiry-001"}

    created = client.post("/api/v1/inquiries", json=payload, headers=headers)
    repeated = client.post(
        "/api/v1/inquiries",
        json={"source": "manual", "raw_message": "Need 120 bottles."},
        headers=headers,
    )
    conflict = client.post(
        "/api/v1/inquiries",
        json={"source": "demo", "raw_message": "Different"},
        headers=headers,
    )

    assert created.status_code == 201
    assert repeated.status_code == 200
    assert repeated.json()["id"] == created.json()["id"]
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
    assert client.get("/inquiries").status_code == 404


def test_missing_key_and_validation_use_safe_error_envelope(
    api_client: tuple[TestClient, FakeDispatcher, Session],
) -> None:
    client, _, _ = api_client
    response = client.post("/api/v1/inquiries", json={"source": "manual", "raw_message": " "})

    assert response.status_code == 422
    assert response.json()["error"]["code"] in {
        "INVALID_INPUT",
        "IDEMPOTENCY_KEY_REQUIRED",
    }
    assert response.json()["error"]["correlation_id"]
    assert "traceback" not in response.text.lower()


def test_inquiry_reads_filter_and_reject_unknown_customer(
    api_client: tuple[TestClient, FakeDispatcher, Session],
) -> None:
    client, _, _ = api_client
    unknown_customer = client.post(
        "/api/v1/inquiries",
        json={
            "source": "manual",
            "raw_message": "Hello",
            "customer_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        },
        headers={"Idempotency-Key": "unknown-customer"},
    )
    invalid_source = client.post(
        "/api/v1/inquiries",
        json={"source": "email_simulated", "raw_message": "Hello"},
        headers={"Idempotency-Key": "bad-source"},
    )
    listing = client.get("/api/v1/inquiries?status=new&limit=1")
    detail = client.get(f"/api/v1/inquiries/{INQUIRY_ID}")

    assert unknown_customer.status_code == 404
    assert unknown_customer.json()["error"]["code"] == "CUSTOMER_NOT_FOUND"
    assert invalid_source.status_code == 422
    assert listing.status_code == 200
    assert listing.json()["limit"] == 1
    assert detail.status_code == 200
    assert detail.json()["raw_message"]
    assert isinstance(detail.json()["agent_runs"], list)


def test_run_is_committed_before_enqueue_and_not_duplicated(
    api_client: tuple[TestClient, FakeDispatcher, Session],
) -> None:
    client, dispatcher, db_session = api_client
    headers = {"Idempotency-Key": "run-001"}

    created = client.post(f"/api/v1/inquiries/{INQUIRY_ID}/agent-runs", headers=headers)
    repeated = client.post(f"/api/v1/inquiries/{INQUIRY_ID}/agent-runs", headers=headers)

    assert created.status_code == 202
    run_id = created.json()["agent_run_id"]
    persisted = db_session.get(AgentRun, run_id)
    assert persisted is not None
    assert persisted.status == "queued"
    assert dispatcher.enqueued == [run_id]
    assert repeated.json()["agent_run_id"] == run_id

    detail = client.get(f"/api/v1/agent-runs/{run_id}")
    events = client.get(f"/api/v1/agent-runs/{run_id}/events")
    result = client.get(f"/api/v1/agent-runs/{run_id}/result")
    assert detail.status_code == 200
    assert detail.json()["last_event_sequence"] == 1
    assert events.json()["events"][0]["event_type"] == "run_created"
    assert result.status_code == 409
    assert result.json()["error"]["code"] == "RUN_NOT_TERMINAL"


def test_interrupted_run_can_retry_without_mutating_original(
    api_client: tuple[TestClient, FakeDispatcher, Session],
) -> None:
    client, dispatcher, db_session = api_client
    repository = AgentRunRepository(db_session)
    original = repository.create_run(
        inquiry_id=INQUIRY_ID,
        model="fake-qwen",
        prompt_versions={},
        request_key="original-run",
    )
    repository.append_event(
        run=original,
        event_type="run_created",
        step=AgentRunStep.QUEUED,
    )
    execution = repository.start_tool_execution(
        run=original,
        tool_name="search_catalog",
        input_payload={"query": "Albariño"},
    )
    interrupted = repository.interrupt_active_runs()
    db_session.commit()

    response = client.post(
        f"/api/v1/agent-runs/{original.id}/retry",
        headers={"Idempotency-Key": "retry-001"},
    )
    repeated = client.post(
        f"/api/v1/agent-runs/{original.id}/retry",
        headers={"Idempotency-Key": "retry-001"},
    )

    assert interrupted == [original.id]
    assert response.status_code == 202
    retry_id = response.json()["agent_run_id"]
    assert retry_id != original.id
    assert response.json()["retry_of_run_id"] == original.id
    assert repeated.json()["agent_run_id"] == retry_id
    assert dispatcher.enqueued == [retry_id]
    db_session.refresh(original)
    assert original.status == "failed"
    assert original.error_code == "RUN_INTERRUPTED"
    assert execution.status == "failed"
    assert execution.error_code == "RUN_INTERRUPTED"


def test_queue_rejection_closes_persisted_run(
    api_client: tuple[TestClient, FakeDispatcher, Session],
) -> None:
    client, dispatcher, session = api_client
    dispatcher.reject = True

    response = client.post(
        f"/api/v1/inquiries/{INQUIRY_ID}/agent-runs",
        headers={"Idempotency-Key": "queue-full"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DISPATCH_QUEUE_FULL"
    run_id = response.json()["error"]["details"]["agent_run_id"]
    run = session.get(AgentRun, run_id)
    assert run is not None
    assert run.status == "failed"
    assert run.error_code == "DISPATCH_QUEUE_FULL"


def test_terminal_partial_result_and_commercial_reads(
    api_client: tuple[TestClient, FakeDispatcher, Session],
) -> None:
    client, _, session = api_client
    repository = AgentRunRepository(session)
    run = repository.create_run(
        inquiry_id=INQUIRY_ID,
        model="fake-qwen",
        prompt_versions={},
    )
    run.result_payload = {
        "recommendation": {"validation_status": "partial"},
        "warnings": ["Manual review required."],
    }
    repository.fail_run(
        run,
        error_code="RUN_LIMIT_REACHED",
        message_safe="The bounded run limit was reached.",
    )
    session.commit()

    result = client.get(f"/api/v1/agent-runs/{run.id}/result")
    run_list = client.get(f"/api/v1/agent-runs?inquiry_id={INQUIRY_ID}")
    memory = client.get("/api/v1/customers/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1/memory")
    opportunity = client.get("/api/v1/opportunities/eeeeeeee-eeee-4eee-8eee-eeeeeeeeeee1")

    assert result.status_code == 200
    assert result.json()["recommendation"]["validation_status"] == "partial"
    assert result.json()["warnings"] == ["Manual review required."]
    assert run_list.status_code == 200
    assert run_list.json()["items"][0]["id"] == run.id
    assert memory.status_code == 200
    assert all(item["content"] for item in memory.json()["items"])
    assert opportunity.status_code == 200
    assert opportunity.json()["id"] == "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeee1"


def test_openapi_has_only_documented_product_prefixes(
    api_client: tuple[TestClient, FakeDispatcher, Session],
) -> None:
    client, _, _ = api_client
    schema = client.get("/openapi.json").json()
    paths = set(schema["paths"])

    assert "/health" in paths
    assert "/api/v1/health" not in paths
    assert "/api/v1/inquiries" in paths
    assert "/api/v1/inquiries/{inquiry_id}/agent-runs" in paths
    assert "/api/v1/agent-runs/{agent_run_id}/retry" in paths
    assert "/api/v1/agent-runs/{agent_run_id}/result" in paths
    assert all(path == "/health" or path.startswith("/api/v1/") for path in paths)


def test_openapi_requires_idempotency_header_on_all_commands(
    api_client: tuple[TestClient, FakeDispatcher, Session],
) -> None:
    client, _, _ = api_client
    schema = client.get("/openapi.json").json()
    command_paths = [
        ("/api/v1/inquiries", "post"),
        ("/api/v1/inquiries/{inquiry_id}/agent-runs", "post"),
        ("/api/v1/agent-runs/{agent_run_id}/retry", "post"),
    ]

    for path, method in command_paths:
        parameters = schema["paths"][path][method]["parameters"]
        header = next(item for item in parameters if item["name"] == "Idempotency-Key")
        assert header["in"] == "header"
        assert header["required"] is True


def test_public_contract_rejects_extras_invalid_uuid_and_query_limits(
    api_client: tuple[TestClient, FakeDispatcher, Session],
) -> None:
    client, _, _ = api_client

    extra = client.post(
        "/api/v1/inquiries",
        json={"source": "demo", "raw_message": "Hello", "unexpected": True},
        headers={"Idempotency-Key": "strict-extra"},
    )
    invalid_uuid = client.get("/api/v1/agent-runs/not-a-uuid")
    invalid_limit = client.get("/api/v1/inquiries?limit=101")

    assert [
        extra.status_code,
        invalid_uuid.status_code,
        invalid_limit.status_code,
    ] == [422, 422, 422]
    assert all(
        response.json()["error"]["code"] == "INVALID_INPUT"
        for response in (extra, invalid_uuid, invalid_limit)
    )


def test_public_events_filter_secrets_and_raw_provider_payloads(
    api_client: tuple[TestClient, FakeDispatcher, Session],
) -> None:
    client, _, session = api_client
    repository = AgentRunRepository(session)
    run = repository.create_run(
        inquiry_id=INQUIRY_ID,
        model="fake-qwen",
        prompt_versions={},
    )
    repository.append_event(
        run=run,
        event_type="provider_failed",
        step=AgentRunStep.FAILED,
        payload={
            "error_code": "QWEN_TIMEOUT",
            "api_key": "secret",
            "raw_response": {"private": True},
            "contact_email": "buyer@example.invalid",
        },
    )
    session.commit()

    response = client.get(f"/api/v1/agent-runs/{run.id}/events")

    assert response.status_code == 200
    assert response.json()["events"][0]["payload"] == {"error_code": "QWEN_TIMEOUT"}
    assert "secret" not in response.text
    assert "buyer@example.invalid" not in response.text


def test_event_cursor_has_no_gaps_or_duplicates(
    api_client: tuple[TestClient, FakeDispatcher, Session],
) -> None:
    client, _, session = api_client
    repository = AgentRunRepository(session)
    run = repository.create_run(
        inquiry_id=INQUIRY_ID,
        model="fake-qwen",
        prompt_versions={},
    )
    for index in range(5):
        repository.append_event(
            run=run,
            event_type=f"event_{index}",
            step=AgentRunStep.QUEUED,
        )
    session.commit()

    first = client.get(f"/api/v1/agent-runs/{run.id}/events?limit=2").json()
    second = client.get(
        f"/api/v1/agent-runs/{run.id}/events?limit=2&after_sequence={first['last_sequence']}"
    ).json()
    third = client.get(
        f"/api/v1/agent-runs/{run.id}/events?limit=2&after_sequence={second['last_sequence']}"
    ).json()
    sequences = [
        item["sequence"]
        for page in (first, second, third)
        for item in page["events"]
    ]

    assert sequences == [1, 2, 3, 4, 5]


def test_failed_run_does_not_borrow_commercial_actions_from_another_run(
    api_client: tuple[TestClient, FakeDispatcher, Session],
) -> None:
    client, _, session = api_client
    repository = AgentRunRepository(session)
    run = repository.create_run(
        inquiry_id=INQUIRY_ID,
        model="fake-qwen",
        prompt_versions={},
    )
    repository.fail_run(
        run,
        error_code="QWEN_TIMEOUT",
        message_safe="Qwen Cloud did not respond before the timeout.",
    )
    session.commit()

    detail = client.get(f"/api/v1/agent-runs/{run.id}").json()
    result = client.get(f"/api/v1/agent-runs/{run.id}/result").json()

    assert detail["references"]["opportunity_id"] is None
    assert detail["references"]["followup_task_id"] is None
    assert result["opportunity"] is None
    assert result["followup"] is None
