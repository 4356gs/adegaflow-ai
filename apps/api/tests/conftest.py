from collections.abc import Iterator
from pathlib import Path

import pytest
from app.db.base import Base
from app.db.models import AgentRun, Inquiry
from app.db.seed import load_seed_file, seed_demo_data
from app.db.session import create_database_engine
from app.repositories.agent_runs import AgentRunRepository
from app.services.quote_calculation import QuoteCalculationResult, QuoteCalculationService
from sqlalchemy.orm import Session

INQUIRY_ID = "dddddddd-dddd-4ddd-8ddd-ddddddddddd1"
PRODUCT_ONE = "11111111-1111-4111-8111-111111111111"
PRODUCT_TWO = "22222222-2222-4222-8222-222222222222"


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


@pytest.fixture
def validated_agent_run(db_session: Session) -> AgentRun:
    inquiry = db_session.get(Inquiry, INQUIRY_ID)
    assert inquiry is not None
    inquiry.detected_language = "en"
    inquiry.extracted_data = {
        "schema_version": "1.0",
        "language": "en",
        "intent": "b2b_purchase_inquiry",
        "market": "DE",
        "product_interest": ["Albariño"],
        "estimated_bottles": 600,
        "channel": "specialty_retail",
        "budget_total_cents": 500000,
        "budget_currency": "EUR",
    }
    repository = AgentRunRepository(db_session)
    run = repository.create_run(
        inquiry_id=INQUIRY_ID,
        model="fake-qwen",
        prompt_versions={},
    )
    run.result_payload = {
        "recommendation": {
            "schema_version": "1.0",
            "items": [
                {
                    "product_id": PRODUCT_ONE,
                    "sku": "ADA-ALB-JOV-2025",
                    "name": "Brétema Albariño 2025",
                    "quantity_bottles": 300,
                    "units_per_case": 6,
                    "cases": 50,
                    "unit_price_cents": 840,
                    "sellable_bottles": 1200,
                    "certifications": [],
                    "rationale": "Fresh style for specialised retail.",
                },
                {
                    "product_id": PRODUCT_TWO,
                    "sku": "ADA-ALB-LIA-2024",
                    "name": "Luar sobre Lías 2024",
                    "quantity_bottles": 300,
                    "units_per_case": 6,
                    "cases": 50,
                    "unit_price_cents": 1190,
                    "sellable_bottles": 720,
                    "certifications": [],
                    "rationale": "Complex style for specialised retail.",
                },
            ],
            "total_bottles": 600,
            "currency": "EUR",
            "summary": "Two complementary Albariño references.",
            "warnings": [],
            "validation_status": "valid",
        }
    }
    db_session.commit()
    return run


@pytest.fixture
def calculated_quote(
    db_session: Session,
    validated_agent_run: AgentRun,
) -> QuoteCalculationResult:
    result = QuoteCalculationService(db_session).calculate(
        validated_agent_run.id
    )
    db_session.commit()
    return result
