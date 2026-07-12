from __future__ import annotations

from uuid import UUID

import pytest
from app.domain.enums import (
    AgentRunStatus,
    AgentRunStep,
    ToolExecutionStatus,
)
from app.repositories.agent_runs import AgentRunRepository
from sqlalchemy.orm import Session

INQUIRY_ID = UUID("dddddddd-dddd-4ddd-8ddd-ddddddddddd1")


def test_run_trace_sequences_and_completion(
    db_session: Session,
) -> None:
    repository = AgentRunRepository(db_session)
    run = repository.create_run(
        inquiry_id=str(INQUIRY_ID),
        model="fake-qwen",
        prompt_versions={"inquiry_analysis": "inquiry_analysis.v1"},
        run_id="77777777-7777-4777-8777-777777777771",
        correlation_id="88888888-8888-4888-8888-888888888881",
    )

    repository.append_event(
        run=run,
        event_type="run_created",
        step=AgentRunStep.QUEUED,
    )
    repository.set_step(run, AgentRunStep.SELECTING_PRODUCTS)
    repository.append_event(
        run=run,
        event_type="step_changed",
        step=AgentRunStep.SELECTING_PRODUCTS,
        payload={"previous_step": "queued"},
    )

    execution = repository.start_tool_execution(
        run=run,
        tool_name="search_catalog",
        input_payload={"query": "Albariño", "market": "DE"},
        execution_id="99999999-9999-4999-8999-999999999991",
    )
    repository.finish_tool_execution(
        execution,
        status=ToolExecutionStatus.SUCCEEDED,
        output_payload={"success": True, "data": {"count": 2}},
        duration_ms=7,
    )
    repository.complete_run(
        run,
        result_payload={"total_bottles": 600},
    )
    db_session.commit()

    events = repository.list_events(run.id)
    executions = repository.list_tool_executions(run.id)

    assert [event.sequence for event in events] == [1, 2]
    assert [event.event_type for event in events] == [
        "run_created",
        "step_changed",
    ]
    assert [item.sequence for item in executions] == [1]
    assert executions[0].status == ToolExecutionStatus.SUCCEEDED.value
    assert executions[0].duration_ms == 7
    assert run.status == AgentRunStatus.COMPLETED.value
    assert run.current_step == AgentRunStep.COMPLETED.value
    assert run.result_payload == {"total_bottles": 600}
    assert run.completed_at is not None


def test_multiple_runs_are_allowed_for_one_inquiry(
    db_session: Session,
) -> None:
    repository = AgentRunRepository(db_session)

    first = repository.create_run(
        inquiry_id=str(INQUIRY_ID),
        model="fake-qwen",
        prompt_versions={},
    )
    second = repository.create_run(
        inquiry_id=str(INQUIRY_ID),
        model="fake-qwen",
        prompt_versions={},
    )
    db_session.commit()

    assert first.id != second.id
    assert first.correlation_id != second.correlation_id
    assert first.inquiry_id == second.inquiry_id


def test_needs_review_and_failed_states_are_safe(
    db_session: Session,
) -> None:
    repository = AgentRunRepository(db_session)
    review_run = repository.create_run(
        inquiry_id=str(INQUIRY_ID),
        model="fake-qwen",
        prompt_versions={},
    )
    failed_run = repository.create_run(
        inquiry_id=str(INQUIRY_ID),
        model="fake-qwen",
        prompt_versions={},
    )

    repository.mark_needs_review(
        review_run,
        result_payload={"partial": True},
        error_code="RUN_LIMIT_REACHED",
        message_safe="The bounded run limit was reached.",
    )
    repository.fail_run(
        failed_run,
        error_code="PERSISTENCE_ERROR",
        message_safe="x" * 800,
    )
    db_session.commit()

    assert review_run.status == AgentRunStatus.NEEDS_REVIEW.value
    assert review_run.result_payload == {"partial": True}
    assert failed_run.status == AgentRunStatus.FAILED.value
    assert failed_run.error_message_safe is not None
    assert len(failed_run.error_message_safe) == 500


def test_unknown_inquiry_is_rejected(
    db_session: Session,
) -> None:
    repository = AgentRunRepository(db_session)

    with pytest.raises(LookupError, match="Inquiry does not exist"):
        repository.create_run(
            inquiry_id="00000000-0000-4000-8000-000000000000",
            model="fake-qwen",
            prompt_versions={},
        )


def test_started_tool_cannot_be_finished_as_started(
    db_session: Session,
) -> None:
    repository = AgentRunRepository(db_session)
    run = repository.create_run(
        inquiry_id=str(INQUIRY_ID),
        model="fake-qwen",
        prompt_versions={},
    )
    execution = repository.start_tool_execution(
        run=run,
        tool_name="search_catalog",
        input_payload={"query": "Albariño"},
    )

    with pytest.raises(ValueError, match="cannot remain started"):
        repository.finish_tool_execution(
            execution,
            status=ToolExecutionStatus.STARTED,
            output_payload={},
            duration_ms=0,
        )
