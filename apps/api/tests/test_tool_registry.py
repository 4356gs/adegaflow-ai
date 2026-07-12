from __future__ import annotations

from app.agent.registry import (
    REGISTERED_TOOL_NAMES,
    SELECTION_TOOL_NAMES,
    ToolRegistry,
)
from app.db.models import AgentRun
from app.domain.enums import (
    AgentRunStep,
    ToolExecutionStatus,
)
from app.repositories.agent_runs import AgentRunRepository
from sqlalchemy.orm import Session

INQUIRY_ID = "dddddddd-dddd-4ddd-8ddd-ddddddddddd1"
CUSTOMER_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1"
PRODUCT_ONE = "11111111-1111-4111-8111-111111111111"
PRODUCT_TWO = "22222222-2222-4222-8222-222222222222"


def build_registry(
    db_session: Session,
) -> tuple[ToolRegistry, AgentRunRepository, AgentRun]:
    repository = AgentRunRepository(db_session)
    run = repository.create_run(
        inquiry_id=INQUIRY_ID,
        model="fake-qwen",
        prompt_versions={},
    )
    repository.set_step(
        run,
        AgentRunStep.SELECTING_PRODUCTS,
    )
    registry = ToolRegistry(db_session, repository)
    return registry, repository, run


def test_registry_exposes_exact_allowlist_and_json_schema(
    db_session: Session,
) -> None:
    registry, _, _ = build_registry(db_session)

    assert registry.names == REGISTERED_TOOL_NAMES
    definitions = registry.definitions()
    assert [
        definition["function"]["name"]
        for definition in definitions
    ] == list(REGISTERED_TOOL_NAMES)

    for definition in definitions:
        parameters = definition["function"]["parameters"]
        assert parameters["type"] == "object"
        assert parameters["additionalProperties"] is False

    selection = registry.selection_definitions()
    assert [
        definition["function"]["name"]
        for definition in selection
    ] == list(SELECTION_TOOL_NAMES)
    assert "retrieve_customer_history" not in {
        definition["function"]["name"]
        for definition in selection
    }


def test_registry_executes_all_approved_read_tools(
    db_session: Session,
) -> None:
    registry, repository, run = build_registry(db_session)

    results = [
        registry.execute(
            run=run,
            tool_name="search_catalog",
            arguments={
                "query": "Albariño",
                "market": "DE",
                "channel": "specialty_retail",
                "limit": 5,
            },
        ),
        registry.execute(
            run=run,
            tool_name="get_product_details",
            arguments={
                "product_ids": [
                    PRODUCT_ONE,
                    PRODUCT_TWO,
                ],
            },
        ),
        registry.execute(
            run=run,
            tool_name="check_stock",
            arguments={
                "items": [
                    {
                        "product_id": PRODUCT_ONE,
                        "requested_bottles": 300,
                    },
                    {
                        "product_id": PRODUCT_TWO,
                        "requested_bottles": 300,
                    },
                ],
            },
        ),
        registry.execute(
            run=run,
            tool_name="retrieve_customer_history",
            arguments={
                "customer_id": CUSTOMER_ID,
                "limit": 20,
            },
        ),
    ]

    assert all(result.success for result in results)
    assert [result.sequence for result in results] == [1, 2, 3, 4]

    executions = repository.list_tool_executions(run.id)
    assert [execution.tool_name for execution in executions] == list(
        REGISTERED_TOOL_NAMES
    )
    assert all(
        execution.status == ToolExecutionStatus.SUCCEEDED.value
        for execution in executions
    )

    events = repository.list_events(run.id)
    assert [event.event_type for event in events] == [
        "tool_requested",
        "tool_started",
        "tool_succeeded",
        "tool_requested",
        "tool_started",
        "tool_succeeded",
        "tool_requested",
        "tool_started",
        "tool_succeeded",
        "tool_requested",
        "tool_started",
        "tool_succeeded",
    ]


def test_unknown_tool_is_rejected_and_traced(
    db_session: Session,
) -> None:
    registry, repository, run = build_registry(db_session)

    result = registry.execute(
        run=run,
        tool_name="run_arbitrary_python",
        arguments={"code": "raise SystemExit"},
    )

    assert result.success is False
    assert result.error_code == "UNKNOWN_TOOL"
    assert result.payload["error"]["code"] == "UNKNOWN_TOOL"

    execution = repository.list_tool_executions(run.id)[0]
    assert execution.tool_name == "run_arbitrary_python"
    assert execution.status == ToolExecutionStatus.REJECTED.value
    assert execution.input_payload == {
        "code": "raise SystemExit",
    }

    events = repository.list_events(run.id)
    assert [event.event_type for event in events] == [
        "tool_requested",
        "tool_rejected",
    ]


def test_invalid_or_extra_arguments_are_rejected(
    db_session: Session,
) -> None:
    registry, repository, run = build_registry(db_session)

    result = registry.execute(
        run=run,
        tool_name="search_catalog",
        arguments={
            "query": "Albariño",
            "unexpected": "not allowed",
        },
    )

    assert result.success is False
    assert result.error_code == "TOOL_INVALID_ARGUMENT"

    execution = repository.list_tool_executions(run.id)[0]
    assert execution.status == ToolExecutionStatus.REJECTED.value
    assert execution.error_code == "TOOL_INVALID_ARGUMENT"


def test_domain_tool_error_is_failed_not_rejected(
    db_session: Session,
) -> None:
    registry, repository, run = build_registry(db_session)

    result = registry.execute(
        run=run,
        tool_name="check_stock",
        arguments={
            "items": [
                {
                    "product_id": (
                        "99999999-9999-4999-8999-999999999999"
                    ),
                    "requested_bottles": 12,
                },
            ],
        },
    )

    assert result.success is False
    assert result.error_code == "NOT_FOUND"
    assert result.retryable is False

    execution = repository.list_tool_executions(run.id)[0]
    assert execution.status == ToolExecutionStatus.FAILED.value
    assert execution.error_code == "NOT_FOUND"

    events = repository.list_events(run.id)
    assert events[-1].event_type == "tool_failed"


def test_unknown_definition_name_is_not_silently_ignored(
    db_session: Session,
) -> None:
    registry, _, _ = build_registry(db_session)

    try:
        registry.definitions(["search_catalog", "unknown"])
    except KeyError as exc:
        assert "unknown" in str(exc)
    else:
        raise AssertionError("Expected an unknown definition to fail.")
