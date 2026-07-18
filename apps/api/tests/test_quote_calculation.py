import pytest
from app.db.models import AgentRun, Inquiry, Quote, QuoteItem
from app.repositories.quote_artifacts import QuoteRepository
from app.services.quote_calculation import QuoteCalculationError, QuoteCalculationService
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def test_calculates_multiple_lines_exactly_and_is_idempotent(
    db_session: Session,
    validated_agent_run: AgentRun,
) -> None:
    service = QuoteCalculationService(db_session)
    first = service.calculate(validated_agent_run.id)
    db_session.commit()
    second = service.calculate(validated_agent_run.id)

    assert first.created is True
    assert second.created is False
    assert second.quote.id == first.quote.id
    assert first.calculated_quote.subtotal_cents == 609000
    assert [item.cases for item in first.calculated_quote.items] == [50, 50]
    assert [item.line_total_cents for item in first.calculated_quote.items] == [
        252000,
        357000,
    ]
    assert first.quote.currency == "EUR"
    assert first.quote.assumptions["stock_reserved"] is False
    assert db_session.scalar(select(func.count()).select_from(Quote)) == 1
    assert db_session.scalar(select(func.count()).select_from(QuoteItem)) == 2


def test_calculates_one_line_and_budget_warning(
    db_session: Session,
    validated_agent_run: AgentRun,
) -> None:
    recommendation = validated_agent_run.result_payload["recommendation"]
    assert isinstance(recommendation, dict)
    recommendation["items"] = [recommendation["items"][0]]
    recommendation["total_bottles"] = 300
    inquiry = db_session.get(Inquiry, validated_agent_run.inquiry_id)
    assert inquiry is not None
    inquiry.extracted_data["budget_total_cents"] = 100000
    db_session.commit()

    result = QuoteCalculationService(db_session).calculate(validated_agent_run.id)

    assert len(result.items) == 1
    assert result.calculated_quote.subtotal_cents == 252000
    assert result.calculated_quote.budget_exceeded is True
    assert "Quote subtotal exceeds the known EUR budget." in result.calculated_quote.warnings


def test_rejects_non_divisible_quantity_without_partial_quote(
    db_session: Session,
    validated_agent_run: AgentRun,
) -> None:
    recommendation = validated_agent_run.result_payload["recommendation"]
    assert isinstance(recommendation, dict)
    items = recommendation["items"]
    assert isinstance(items, list)
    items[0]["quantity_bottles"] = 301
    recommendation["total_bottles"] = 601
    db_session.commit()

    with pytest.raises(QuoteCalculationError) as captured:
        QuoteCalculationService(db_session).calculate(validated_agent_run.id)

    assert captured.value.code == "QUOTE_ARITHMETIC_ERROR"
    assert QuoteRepository(db_session).get_by_run_id(validated_agent_run.id) is None


def test_rejects_non_eur_and_idempotency_conflict(
    db_session: Session,
    validated_agent_run: AgentRun,
) -> None:
    recommendation = validated_agent_run.result_payload["recommendation"]
    assert isinstance(recommendation, dict)
    recommendation["currency"] = "USD"
    db_session.commit()
    with pytest.raises(QuoteCalculationError) as captured:
        QuoteCalculationService(db_session).calculate(validated_agent_run.id)
    assert captured.value.code == "UNSUPPORTED_QUOTE_CURRENCY"
    assert captured.value.needs_review is True

    recommendation["currency"] = "EUR"
    first = QuoteCalculationService(db_session).calculate(validated_agent_run.id)
    db_session.commit()
    items = recommendation["items"]
    assert isinstance(items, list)
    items[0]["unit_price_cents"] = 841
    db_session.commit()
    with pytest.raises(QuoteCalculationError) as conflict:
        QuoteCalculationService(db_session).calculate(validated_agent_run.id)
    assert conflict.value.code == "QUOTE_IDEMPOTENCY_CONFLICT"
    assert conflict.value.needs_review is True
    db_session.rollback()
    assert QuoteRepository(db_session).get_by_run_id(validated_agent_run.id).id == first.quote.id
