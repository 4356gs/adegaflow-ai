import asyncio

import pytest
from app.core.config import Settings
from app.db.base import Base
from app.db.session import create_database_engine
from app.services.async_runs import LocalRunDispatcher, QueueFullError, is_retryable
from sqlalchemy.orm import Session, sessionmaker


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
