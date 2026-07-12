"""Persistence boundary for agent runs, tool executions and events."""

from __future__ import annotations

from collections.abc import Mapping
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    AgentRun,
    AgentRunEvent,
    Inquiry,
    ToolExecution,
    utc_now,
)
from app.domain.enums import (
    AgentRunStatus,
    AgentRunStep,
    ToolExecutionStatus,
)

JsonPayload = Mapping[str, object]


class AgentRunRepository:
    """Store orchestration state without owning transaction commits."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_run(
        self,
        *,
        inquiry_id: str,
        model: str,
        prompt_versions: JsonPayload,
        run_id: str | None = None,
        correlation_id: str | None = None,
    ) -> AgentRun:
        if self._session.get(Inquiry, inquiry_id) is None:
            raise LookupError("Inquiry does not exist.")

        run = AgentRun(
            id=run_id or str(uuid4()),
            inquiry_id=inquiry_id,
            correlation_id=correlation_id or str(uuid4()),
            status=AgentRunStatus.QUEUED.value,
            model=model,
            prompt_versions=dict(prompt_versions),
            result_payload={},
            current_step=AgentRunStep.QUEUED.value,
        )
        self._session.add(run)
        self._session.flush()
        return run

    def get_by_id(self, run_id: str) -> AgentRun | None:
        return self._session.get(AgentRun, run_id)

    def set_step(self, run: AgentRun, step: AgentRunStep) -> None:
        run.current_step = step.value
        if step not in {
            AgentRunStep.COMPLETED,
            AgentRunStep.NEEDS_REVIEW,
            AgentRunStep.FAILED,
        }:
            run.status = AgentRunStatus.RUNNING.value

    def append_event(
        self,
        *,
        run: AgentRun,
        event_type: str,
        step: AgentRunStep,
        payload: JsonPayload | None = None,
        event_id: str | None = None,
    ) -> AgentRunEvent:
        event = AgentRunEvent(
            id=event_id or str(uuid4()),
            agent_run_id=run.id,
            sequence=self._next_event_sequence(run.id),
            event_type=event_type,
            step=step.value,
            payload=dict(payload or {}),
        )
        self._session.add(event)
        self._session.flush()
        return event

    def start_tool_execution(
        self,
        *,
        run: AgentRun,
        tool_name: str,
        input_payload: JsonPayload,
        execution_id: str | None = None,
    ) -> ToolExecution:
        execution = ToolExecution(
            id=execution_id or str(uuid4()),
            agent_run_id=run.id,
            sequence=self._next_tool_sequence(run.id),
            tool_name=tool_name,
            input_payload=dict(input_payload),
            output_payload={},
            status=ToolExecutionStatus.STARTED.value,
            duration_ms=0,
        )
        self._session.add(execution)
        self._session.flush()
        return execution

    def finish_tool_execution(
        self,
        execution: ToolExecution,
        *,
        status: ToolExecutionStatus,
        output_payload: JsonPayload,
        duration_ms: int,
        error_code: str | None = None,
    ) -> None:
        if status is ToolExecutionStatus.STARTED:
            raise ValueError(
                "A completed tool execution cannot remain started."
            )
        if duration_ms < 0:
            raise ValueError("duration_ms must be non-negative.")

        execution.status = status.value
        execution.output_payload = dict(output_payload)
        execution.duration_ms = duration_ms
        execution.error_code = error_code

    def complete_run(
        self,
        run: AgentRun,
        *,
        result_payload: JsonPayload,
    ) -> None:
        run.status = AgentRunStatus.COMPLETED.value
        run.current_step = AgentRunStep.COMPLETED.value
        run.result_payload = dict(result_payload)
        run.completed_at = utc_now()
        run.error_code = None
        run.error_message_safe = None

    def mark_needs_review(
        self,
        run: AgentRun,
        *,
        result_payload: JsonPayload,
        error_code: str,
        message_safe: str,
    ) -> None:
        run.status = AgentRunStatus.NEEDS_REVIEW.value
        run.current_step = AgentRunStep.NEEDS_REVIEW.value
        run.result_payload = dict(result_payload)
        run.completed_at = utc_now()
        run.error_code = error_code
        run.error_message_safe = message_safe[:500]

    def fail_run(
        self,
        run: AgentRun,
        *,
        error_code: str,
        message_safe: str,
    ) -> None:
        run.status = AgentRunStatus.FAILED.value
        run.current_step = AgentRunStep.FAILED.value
        run.completed_at = utc_now()
        run.error_code = error_code
        run.error_message_safe = message_safe[:500]

    def list_events(self, run_id: str) -> list[AgentRunEvent]:
        statement = (
            select(AgentRunEvent)
            .where(AgentRunEvent.agent_run_id == run_id)
            .order_by(AgentRunEvent.sequence)
        )
        return list(self._session.scalars(statement))

    def list_tool_executions(
        self,
        run_id: str,
    ) -> list[ToolExecution]:
        statement = (
            select(ToolExecution)
            .where(ToolExecution.agent_run_id == run_id)
            .order_by(ToolExecution.sequence)
        )
        return list(self._session.scalars(statement))

    def _next_event_sequence(self, run_id: str) -> int:
        statement = select(func.max(AgentRunEvent.sequence)).where(
            AgentRunEvent.agent_run_id == run_id
        )
        current = self._session.scalar(statement)
        return int(current or 0) + 1

    def _next_tool_sequence(self, run_id: str) -> int:
        statement = select(func.max(ToolExecution.sequence)).where(
            ToolExecution.agent_run_id == run_id
        )
        current = self._session.scalar(statement)
        return int(current or 0) + 1
