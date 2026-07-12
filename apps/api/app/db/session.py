"""Database engine and session helpers."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def _ensure_sqlite_parent(database_url: str) -> None:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite":
        return

    database = url.database
    if database is None or database in {"", ":memory:"}:
        return

    Path(database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


def create_database_engine(database_url: str, *, echo: bool = False) -> Engine:
    """Create an engine with SQLite safety settings when applicable."""

    _ensure_sqlite_parent(database_url)
    connect_args: dict[str, object] = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_engine(
        database_url,
        echo=echo,
        future=True,
        connect_args=connect_args,
    )

    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection: object, _: object) -> None:
            cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


settings = get_settings()
engine = create_database_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


@contextmanager
def session_scope(session_factory: sessionmaker[Session] = SessionLocal) -> Iterator[Session]:
    """Commit one unit of work or roll it back on failure."""

    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
