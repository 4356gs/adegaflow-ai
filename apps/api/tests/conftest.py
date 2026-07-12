from collections.abc import Iterator
from pathlib import Path

import pytest
from app.db.base import Base
from app.db.seed import load_seed_file, seed_demo_data
from app.db.session import create_database_engine
from sqlalchemy.orm import Session


@pytest.fixture
def db_session() -> Iterator[Session]:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    seed_path = Path(__file__).resolve().parents[3] / "data/seeds/demo_seed.json"

    with Session(engine, expire_on_commit=False) as session:
        seed_demo_data(session, load_seed_file(seed_path))
        session.commit()
        yield session

    engine.dispose()
