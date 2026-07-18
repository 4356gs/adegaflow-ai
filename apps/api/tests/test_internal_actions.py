from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.db.models import (
    Customer,
    CustomerMemory,
    FollowUpTask,
    GeneratedArtifact,
    Inquiry,
    InternalActionReceipt,
    Inventory,
    Opportunity,
)
from app.domain.enums import AgentRunStatus, ArtifactType
from app.repositories.agent_runs import AgentRunRepository
from app.repositories.internal_actions import InternalActionRepository
from app.repositories.quote_artifacts import GeneratedArtifactRepository
from app.services.internal_actions import InternalActionError, InternalActionsService
from app.services.quote_calculation import QuoteCalculationResult
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

INQUIRY_ID = "dddddddd-dddd-4ddd-8ddd-ddddddddddd1"
FIXED_NOW = datetime(2026, 7, 18, 15, 0, tzinfo=UTC)


def _prepare_artifacts(session: Session, calculated_quote: QuoteCalculationResult) -> str:
    run = calculated_quote.quote.agent_run_id
    session.execute(delete(Opportunity).where(Opportunity.inquiry_id == INQUIRY_ID))
    repository = GeneratedArtifactRepository(session)
    for artifact_type in (ArtifactType.PROPOSAL, ArtifactType.EMAIL_DRAFT):
        repository.create_or_get(
            agent_run_id=run,
            quote_id=calculated_quote.quote.id,
            artifact_type=artifact_type,
            language="en",
            schema_version="1.0",
            content={"artifact_type": artifact_type.value},
        )
    session.commit()
    return run


def test_internal_actions_are_atomic_traceable_and_idempotent(
    db_session: Session,
    calculated_quote: QuoteCalculationResult,
) -> None:
    run_id = _prepare_artifacts(db_session, calculated_quote)
    before_inventory = list(
        db_session.execute(
            select(
                Inventory.product_id,
                Inventory.available_bottles,
                Inventory.reserved_bottles,
            ).order_by(Inventory.product_id)
        )
    )
    service = InternalActionsService(db_session, clock=lambda: FIXED_NOW)

    result = service.execute(run_id)
    db_session.commit()

    assert result.opportunity.score == 85
    assert result.followup.due_at == FIXED_NOW + timedelta(days=7)
    followup = db_session.get(FollowUpTask, str(result.followup.followup_task_id))
    assert followup is not None
    assert followup.title == "Follow up on proposal and pricing"
    assert result.memory.saved_count >= 3
    assert db_session.scalar(select(func.count()).select_from(Opportunity)) == 1
    assert db_session.scalar(select(func.count()).select_from(FollowUpTask)) == 1
    assert db_session.scalar(select(func.count()).select_from(InternalActionReceipt)) == 3
    assert db_session.scalar(select(func.count()).select_from(CustomerMemory)) >= 4
    run = AgentRunRepository(db_session).get_by_id(run_id)
    assert run is not None
    assert run.status == AgentRunStatus.NEEDS_REVIEW.value
    assert set(run.result_payload) >= {
        "recommendation",
        "customer",
        "opportunity",
        "followup",
        "memory",
    }
    assert "email" not in run.result_payload["customer"]
    assert before_inventory == list(
        db_session.execute(
            select(
                Inventory.product_id,
                Inventory.available_bottles,
                Inventory.reserved_bottles,
            ).order_by(Inventory.product_id)
        )
    )

    with Session(db_session.get_bind(), expire_on_commit=False) as second_session:
        second = InternalActionsService(
            second_session, clock=lambda: FIXED_NOW
        ).execute(run_id)
        second_session.commit()
    assert second.opportunity.opportunity_id == result.opportunity.opportunity_id
    assert second.followup.followup_task_id == result.followup.followup_task_id
    assert second.memory.memory_ids == result.memory.memory_ids
    assert db_session.scalar(select(func.count()).select_from(Opportunity)) == 1
    assert db_session.scalar(select(func.count()).select_from(FollowUpTask)) == 1
    assert db_session.scalar(select(func.count()).select_from(InternalActionReceipt)) == 3
    executions = AgentRunRepository(db_session).list_tool_executions(run_id)
    assert [item.tool_name for item in executions[-3:]] == [
        "create_crm_opportunity",
        "create_followup_task",
        "save_customer_memory",
    ]
    assert all(item.output_payload["reused"] for item in executions[-3:])


def test_unknown_identifiable_buyer_gets_minimal_customer_without_matching(
    db_session: Session,
    calculated_quote: QuoteCalculationResult,
) -> None:
    run_id = _prepare_artifacts(db_session, calculated_quote)
    run = AgentRunRepository(db_session).get_by_id(run_id)
    assert run is not None
    inquiry = db_session.get(Inquiry, run.inquiry_id)
    assert inquiry is not None
    inquiry.customer_id = None
    inquiry.extracted_data = {
        **inquiry.extracted_data,
        "company_name": "New Atlantic Imports",
        "market": "FR",
        "language": "fr",
        "contact_name": "Camille Martin",
        "contact_email": "camille@example.test",
    }
    same_email_customer = Customer(
        id=str(uuid4()),
        company_name="Unrelated Existing Buyer",
        country_code="FR",
        contact_name="Another Person",
        email="camille@example.test",
        preferred_language="fr",
    )
    db_session.add(same_email_customer)
    existing_customer_count = db_session.scalar(
        select(func.count()).select_from(Customer)
    )
    db_session.commit()

    result = InternalActionsService(
        db_session, clock=lambda: FIXED_NOW
    ).execute(run_id)
    db_session.commit()

    assert result.customer.created is True
    customer = db_session.get(Customer, str(result.customer.customer_id))
    assert customer is not None
    assert customer.company_name == "New Atlantic Imports"
    assert customer.country_code == "FR"
    assert customer.preferred_language == "fr"
    assert customer.id != same_email_customer.id
    assert db_session.scalar(select(func.count()).select_from(Customer)) == (
        existing_customer_count + 1
    )


def test_failure_during_followup_rolls_back_entire_action_unit(
    db_session: Session,
    calculated_quote: QuoteCalculationResult,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = _prepare_artifacts(db_session, calculated_quote)

    def fail_followup(
        _repository: InternalActionRepository, **_values: object
    ) -> FollowUpTask:
        from sqlalchemy.exc import OperationalError

        raise OperationalError("INSERT", {}, RuntimeError("synthetic"))

    monkeypatch.setattr(InternalActionRepository, "add_followup", fail_followup)
    with pytest.raises(InternalActionError) as exc_info:
        InternalActionsService(db_session, clock=lambda: FIXED_NOW).execute(run_id)
    db_session.rollback()

    assert exc_info.value.code == "INTERNAL_ACTION_PERSISTENCE_ERROR"
    assert db_session.scalar(select(func.count()).select_from(Opportunity)) == 0
    assert db_session.scalar(select(func.count()).select_from(FollowUpTask)) == 0
    assert (
        db_session.scalar(select(func.count()).select_from(InternalActionReceipt))
        == 0
    )


def test_insufficient_new_customer_identity_creates_no_actions(
    db_session: Session,
    calculated_quote: QuoteCalculationResult,
) -> None:
    run_id = _prepare_artifacts(db_session, calculated_quote)
    run = AgentRunRepository(db_session).get_by_id(run_id)
    assert run is not None
    inquiry = db_session.get(Inquiry, run.inquiry_id)
    assert inquiry is not None
    inquiry.customer_id = None
    inquiry.extracted_data = {
        **inquiry.extracted_data,
        "company_name": None,
        "market": None,
    }
    customer_count = db_session.scalar(select(func.count()).select_from(Customer))
    db_session.commit()

    with pytest.raises(InternalActionError) as exc_info:
        InternalActionsService(db_session, clock=lambda: FIXED_NOW).execute(run_id)
    db_session.rollback()

    assert exc_info.value.code == "INTERNAL_ACTION_VALIDATION_FAILED"
    assert db_session.scalar(select(func.count()).select_from(Customer)) == customer_count
    assert db_session.scalar(select(func.count()).select_from(Opportunity)) == 0
    assert (
        db_session.scalar(select(func.count()).select_from(InternalActionReceipt))
        == 0
    )


def test_changed_followup_fingerprint_is_rejected_without_overwrite(
    db_session: Session,
    calculated_quote: QuoteCalculationResult,
) -> None:
    run_id = _prepare_artifacts(db_session, calculated_quote)
    InternalActionsService(db_session, clock=lambda: FIXED_NOW).execute(run_id)
    db_session.commit()
    original = db_session.scalar(select(FollowUpTask))
    assert original is not None
    original_due_at = original.due_at

    with pytest.raises(InternalActionError) as exc_info:
        InternalActionsService(db_session, clock=lambda: FIXED_NOW + timedelta(hours=1)).execute(
            run_id
        )
    db_session.rollback()

    assert exc_info.value.code == "IDEMPOTENCY_CONFLICT"
    persisted = db_session.scalar(select(FollowUpTask))
    assert persisted is not None
    assert persisted.due_at == original_due_at
    assert db_session.scalar(select(func.count()).select_from(FollowUpTask)) == 1


def test_internal_actions_require_both_reviewable_artifacts(
    db_session: Session,
    calculated_quote: QuoteCalculationResult,
) -> None:
    run_id = calculated_quote.quote.agent_run_id
    db_session.execute(delete(GeneratedArtifact))
    db_session.execute(delete(Opportunity).where(Opportunity.inquiry_id == INQUIRY_ID))
    db_session.commit()

    with pytest.raises(InternalActionError) as exc_info:
        InternalActionsService(db_session, clock=lambda: FIXED_NOW).execute(run_id)
    db_session.rollback()

    assert exc_info.value.code == "INTERNAL_ACTION_VALIDATION_FAILED"
    assert db_session.scalar(select(func.count()).select_from(FollowUpTask)) == 0
    assert db_session.scalar(select(func.count()).select_from(InternalActionReceipt)) == 0
