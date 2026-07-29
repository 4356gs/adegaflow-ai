import asyncio

import pytest
from app.core.config import Settings
from app.db.base import Base
from app.db.session import create_database_engine
from app.services.async_runs import LocalRunDispatcher, QueueFullError, is_retryable
from sqlalchemy.orm import Session, sessionmaker


class UnusedClient:
    pass


def test_retry_policy_is_closed() -> None:
    assert is_retryable(status="failed", error_code="QWEN_TIMEOUT") is True
    assert is_retryable(status="needs_review", error_code="QWEN_TIMEOUT") is False
    assert is_retryable(status="failed", error_code="RUN_LIMIT_REACHED") is False


def test_dispatcher_queue_is_bounded(tmp_path) -> None:  # type: ignore[no-untyped-def]
    engine = create_database_engine(f"sqlite:///{tmp_path / 'queue.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    dispatcher = LocalRunDispatcher(
        session_factory=factory,
        settings=Settings(ASYNC_RUN_QUEUE_CAPACITY=1),
    )

    dispatcher.enqueue("first")
    with pytest.raises(QueueFullError):
        dispatcher.enqueue("second")
    engine.dispose()


def test_dispatcher_lifecycle_starts_and_stops_one_consumer(tmp_path) -> None:  # type: ignore[no-untyped-def]
    engine = create_database_engine(f"sqlite:///{tmp_path / 'lifecycle.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    dispatcher = LocalRunDispatcher(
        session_factory=factory,
        settings=Settings(ASYNC_RUN_QUEUE_CAPACITY=2),
    )

    async def exercise() -> None:
        await dispatcher.start()
        first_consumer = dispatcher._consumer
        await dispatcher.start()
        assert dispatcher._consumer is first_consumer
        assert first_consumer is not None
        await dispatcher.stop()
        assert dispatcher._consumer is None

    asyncio.run(exercise())
    engine.dispose()


def test_dispatcher_uses_injected_client_factory_per_run(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    engine = create_database_engine(f"sqlite:///{tmp_path / 'factory.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    clients: list[UnusedClient] = []
    processed: list[tuple[str, object]] = []

    def client_factory(_session: Session) -> UnusedClient:
        client = UnusedClient()
        clients.append(client)
        return client

    class FakeOrchestrator:
        def __init__(self, _session, client, *, model) -> None:  # type: ignore[no-untyped-def]
            processed.append((model, client))

        def run(self, inquiry_id: str, *, run_id: str) -> None:
            processed.append((inquiry_id, run_id))

    monkeypatch.setattr(
        "app.services.async_runs.BoundedRecommendationOrchestrator",
        FakeOrchestrator,
    )
    dispatcher = LocalRunDispatcher(
        session_factory=factory,
        settings=Settings(),
        client_factory=client_factory,  # type: ignore[arg-type]
    )

    from app.db.models import AgentRun, Inquiry

    with factory() as session:
        inquiry = Inquiry(id="inquiry", source="demo", raw_message="message", submission_key="key")
        session.add(inquiry)
        session.commit()
        run = AgentRun(
            id="run",
            inquiry_id="inquiry",
            status="queued",
            current_step="queued",
            model="fake-qwen",
            prompt_versions={},
            correlation_id="11111111-1111-4111-8111-111111111111",
        )
        session.add(run)
        session.commit()

    dispatcher._process("run")

    assert len(clients) == 1
    assert processed == [
        ("fake-qwen", clients[0]),
        ("inquiry", "run"),
    ]
    engine.dispose()
