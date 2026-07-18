import pytest
from app.db.models import AgentRun, Customer, Inquiry
from app.domain.artifacts import (
    ALLOWED_EMAIL_NEXT_STEPS,
    ALLOWED_PROPOSAL_NEXT_STEPS,
    EmailDraftNarrative,
    ProposalNarrative,
)
from app.repositories.quote_artifacts import GeneratedArtifactRepository
from app.services.artifact_persistence import ArtifactPersistenceError, ArtifactPersistenceService
from app.services.quote_calculation import QuoteCalculationResult
from sqlalchemy.orm import Session

PRODUCT_ONE = "11111111-1111-4111-8111-111111111111"
UNKNOWN_PRODUCT = "99999999-9999-4999-8999-999999999999"


def proposal_narrative(product_id: str = PRODUCT_ONE) -> ProposalNarrative:
    return ProposalNarrative.model_validate(
        {
            "headline": "Galician wines for specialised retail",
            "executive_summary": "A focused selection for human review.",
            "product_positioning": [
                {"product_id": product_id, "positioning": "Fresh Atlantic style."}
            ],
            "next_steps": [ALLOWED_PROPOSAL_NEXT_STEPS[0]],
            "open_questions": [],
            "warnings": ["Human review is required."],
        }
    )


def email_narrative() -> EmailDraftNarrative:
    return EmailDraftNarrative(
        subject="Draft proposal for review",
        introduction="Thank you for your inquiry.",
        recommendation_summary="We prepared a focused selection.",
        next_step=ALLOWED_EMAIL_NEXT_STEPS[0],
        questions=[],
        closing="Kind regards",
        warnings=["Human review is required before sending."],
    )


def test_persists_proposal_and_email_with_authoritative_quote(
    db_session: Session,
    validated_agent_run: AgentRun,
    calculated_quote: QuoteCalculationResult,
) -> None:
    service = ArtifactPersistenceService(db_session)
    proposal = service.persist_proposal(
        agent_run_id=validated_agent_run.id,
        quote_id=calculated_quote.quote.id,
        narrative=proposal_narrative(),
    )
    db_session.commit()
    email = service.persist_email_draft(
        agent_run_id=validated_agent_run.id,
        quote_id=calculated_quote.quote.id,
        proposal_artifact_id=proposal.artifact.id,
        narrative=email_narrative(),
    )
    db_session.commit()

    assert proposal.content.quote.subtotal_cents == 609000
    assert proposal.content.quote.lines[0].unit_price_cents == 840
    assert proposal.content.language == "en"
    assert email.content.commercial_block.subtotal_cents == 609000
    assert str(email.content.proposal_artifact_id) == proposal.artifact.id
    assert proposal.artifact.review_status == "needs_review"
    assert email.artifact.review_status == "needs_review"
    assert len(GeneratedArtifactRepository(db_session).list_by_run(validated_agent_run.id)) == 2


def test_artifacts_are_idempotent_and_conflicts_do_not_overwrite(
    db_session: Session,
    validated_agent_run: AgentRun,
    calculated_quote: QuoteCalculationResult,
) -> None:
    service = ArtifactPersistenceService(db_session)
    first = service.persist_proposal(
        agent_run_id=validated_agent_run.id,
        quote_id=calculated_quote.quote.id,
        narrative=proposal_narrative(),
    )
    db_session.commit()
    repeated = service.persist_proposal(
        agent_run_id=validated_agent_run.id,
        quote_id=calculated_quote.quote.id,
        narrative=proposal_narrative(),
    )
    assert repeated.created is False
    assert repeated.artifact.id == first.artifact.id

    changed = proposal_narrative().model_copy(update={"headline": "Changed headline"})
    with pytest.raises(ArtifactPersistenceError) as captured:
        service.persist_proposal(
            agent_run_id=validated_agent_run.id,
            quote_id=calculated_quote.quote.id,
            narrative=changed,
        )
    assert captured.value.code == "ARTIFACT_IDEMPOTENCY_CONFLICT"
    assert captured.value.needs_review is True


def test_rejects_product_outside_quote(
    db_session: Session,
    validated_agent_run: AgentRun,
    calculated_quote: QuoteCalculationResult,
) -> None:
    with pytest.raises(ArtifactPersistenceError) as captured:
        ArtifactPersistenceService(db_session).persist_proposal(
            agent_run_id=validated_agent_run.id,
            quote_id=calculated_quote.quote.id,
            narrative=proposal_narrative(UNKNOWN_PRODUCT),
        )
    assert captured.value.code == "PROPOSAL_PRODUCT_MISMATCH"
    assert GeneratedArtifactRepository(db_session).list_by_run(validated_agent_run.id) == []


def test_rejects_unauthorized_proposal_next_step_without_persisting_artifact(
    db_session: Session,
    validated_agent_run: AgentRun,
    calculated_quote: QuoteCalculationResult,
) -> None:
    narrative = proposal_narrative().model_copy(
        update={"next_steps": ["Send the proposal automatically."]}
    )

    with pytest.raises(ArtifactPersistenceError) as captured:
        ArtifactPersistenceService(db_session).persist_proposal(
            agent_run_id=validated_agent_run.id,
            quote_id=calculated_quote.quote.id,
            narrative=narrative,
        )

    assert captured.value.code == "PROPOSAL_NEXT_STEP_NOT_ALLOWED"
    assert captured.value.needs_review is True
    assert GeneratedArtifactRepository(db_session).list_by_run(validated_agent_run.id) == []
    assert calculated_quote.quote.id is not None


def test_rejects_unauthorized_email_next_step_and_preserves_proposal(
    db_session: Session,
    validated_agent_run: AgentRun,
    calculated_quote: QuoteCalculationResult,
) -> None:
    service = ArtifactPersistenceService(db_session)
    proposal = service.persist_proposal(
        agent_run_id=validated_agent_run.id,
        quote_id=calculated_quote.quote.id,
        narrative=proposal_narrative(),
    )
    db_session.commit()
    narrative = email_narrative().model_copy(
        update={"next_step": "Send the email automatically."}
    )

    with pytest.raises(ArtifactPersistenceError) as captured:
        service.persist_email_draft(
            agent_run_id=validated_agent_run.id,
            quote_id=calculated_quote.quote.id,
            proposal_artifact_id=proposal.artifact.id,
            narrative=narrative,
        )

    assert captured.value.code == "EMAIL_NEXT_STEP_NOT_ALLOWED"
    assert captured.value.needs_review is True
    persisted = GeneratedArtifactRepository(db_session).list_by_run(
        validated_agent_run.id
    )
    assert [artifact.artifact_type for artifact in persisted] == ["proposal"]
    assert calculated_quote.quote.id is not None


def test_language_falls_back_to_customer_then_english(
    db_session: Session,
    validated_agent_run: AgentRun,
    calculated_quote: QuoteCalculationResult,
) -> None:
    inquiry = db_session.get(Inquiry, validated_agent_run.inquiry_id)
    assert inquiry is not None
    inquiry.detected_language = "invalid"
    assert inquiry.customer_id is not None
    db_customer = db_session.get(Customer, inquiry.customer_id)
    assert db_customer is not None
    db_customer.preferred_language = "es"
    db_session.commit()
    result = ArtifactPersistenceService(db_session).persist_proposal(
        agent_run_id=validated_agent_run.id,
        quote_id=calculated_quote.quote.id,
        narrative=proposal_narrative(),
    )
    assert result.content.language == "es"


def test_language_falls_back_to_english_without_customer(
    db_session: Session,
    validated_agent_run: AgentRun,
    calculated_quote: QuoteCalculationResult,
) -> None:
    inquiry = db_session.get(Inquiry, validated_agent_run.inquiry_id)
    assert inquiry is not None
    inquiry.detected_language = "invalid"
    inquiry.customer_id = None
    db_session.commit()
    result = ArtifactPersistenceService(db_session).persist_proposal(
        agent_run_id=validated_agent_run.id,
        quote_id=calculated_quote.quote.id,
        narrative=proposal_narrative(),
    )
    assert result.content.language == "en"
