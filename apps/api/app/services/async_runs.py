"""In-process asynchronous dispatcher and closed retry policy."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Protocol

from sqlalchemy.orm import Session, sessionmaker

from app.agent.orchestrator import (
    BoundedRecommendationOrchestrator,
    RecommendationModelClient,
)
from app.ai.qwen_client import QwenClient
from app.core.config import Settings
from app.domain.enums import AgentRunStatus, AgentRunStep
from app.repositories.agent_runs import AgentRunRepository

logger = logging.getLogger(__name__)

RETRYABLE_ERROR_CODES = frozenset(
    {
        "MODEL_TIMEOUT",
        "MODEL_RATE_LIMIT",
        "QWEN_TIMEOUT",
        "QWEN_RATE_LIMITED",
        "QWEN_CONNECTION_FAILED",
        "PERSISTENCE_ERROR",
        "RUN_INTERRUPTED",
        "DISPATCH_FAILED",
        "DISPATCH_QUEUE_FULL",
    }
)
TERMINAL_STATUSES = frozenset(
    {
        AgentRunStatus.COMPLETED.value,
        AgentRunStatus.NEEDS_REVIEW.value,
        AgentRunStatus.FAILED.value,
    }
)


def is_retryable(*, status: str, error_code: str | None) -> bool:
    return status == AgentRunStatus.FAILED.value and error_code in RETRYABLE_ERROR_CODES


class RunDispatcher(Protocol):
    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    def enqueue(self, run_id: str) -> None: ...


class QueueFullError(RuntimeError):
    """Raised when the bounded local queue cannot accept work."""


class LocalRunDispatcher:
    """FIFO dispatcher with exactly one background consumer."""

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        settings: Settings,
        client_factory: Callable[[Session], RecommendationModelClient] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._client_factory = client_factory or (lambda _session: QwenClient(settings))
        self._queue: asyncio.Queue[str | None] = asyncio.Queue(
            maxsize=settings.async_run_queue_capacity
        )
        self._consumer: asyncio.Task[None] | None = None
        self._scheduled: set[str] = set()

    async def start(self) -> None:
        if self._consumer is not None:
            return
        await asyncio.to_thread(self._recover_interrupted)
        self._consumer = asyncio.create_task(self._consume(), name="adegaflow-agent-run-consumer")

    async def stop(self) -> None:
        consumer = self._consumer
        if consumer is None:
            return
        await self._queue.put(None)
        await consumer
        self._consumer = None

    def enqueue(self, run_id: str) -> None:
        if run_id in self._scheduled:
            return
        try:
            self._queue.put_nowait(run_id)
        except asyncio.QueueFull as exc:
            raise QueueFullError("The local run queue is full.") from exc
        self._scheduled.add(run_id)

    async def _consume(self) -> None:
        while True:
            run_id = await self._queue.get()
            try:
                if run_id is None:
                    return
                await asyncio.to_thread(self._process, run_id)
            finally:
                if run_id is not None:
                    self._scheduled.discard(run_id)
                self._queue.task_done()

    def _recover_interrupted(self) -> None:
        with self._session_factory() as session:
            repository = AgentRunRepository(session)
            interrupted = repository.interrupt_active_runs()
            session.commit()
            if interrupted:
                logger.warning(
                    "agent_runs_interrupted",
                    extra={"run_count": len(interrupted)},
                )

    def _process(self, run_id: str) -> None:
        with self._session_factory() as session:
            repository = AgentRunRepository(session)
            run = repository.get_by_id(run_id)
            if run is None or run.status != AgentRunStatus.QUEUED.value:
                return
            inquiry_id = run.inquiry_id
            try:
                BoundedRecommendationOrchestrator(
                    session,
                    self._client_factory(session),
                    model=run.model,
                ).run(inquiry_id, run_id=run.id)
            except Exception:
                session.rollback()
                run = repository.get_by_id(run_id)
                if run is not None and run.status not in TERMINAL_STATUSES:
                    repository.fail_run(
                        run,
                        error_code="PERSISTENCE_ERROR",
                        message_safe="The agent run could not be completed safely.",
                    )
                    repository.append_event(
                        run=run,
                        event_type="run_failed",
                        step=AgentRunStep.FAILED,
                        payload={"error_code": "PERSISTENCE_ERROR"},
                    )
                    session.commit()
                logger.exception("agent_run_worker_failed", extra={"run_id": run_id})
