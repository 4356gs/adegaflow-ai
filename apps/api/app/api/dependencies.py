"""FastAPI dependency boundaries for sessions and command headers."""

import re
from collections.abc import Iterator

from fastapi import Header
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.db.session import SessionLocal

IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9._:/+\-=]{1,160}$")


def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def require_idempotency_key(
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> str:
    normalized = idempotency_key.strip()
    if not IDEMPOTENCY_KEY_PATTERN.fullmatch(normalized):
        raise ApiError(
            422,
            "INVALID_INPUT",
            "Idempotency-Key must use 1-160 safe ASCII characters.",
        )
    return normalized
