from uuid import UUID

import pytest
from app.ai.prompts import load_email_writer_prompt, load_proposal_writer_prompt
from app.domain.artifacts import (
    ArtifactQuoteLine,
    ArtifactQuoteSnapshot,
    EmailDraftNarrative,
    ProposalNarrative,
)
from app.domain.quote import CalculatedQuote, CalculatedQuoteItem, QuoteAssumptions
from pydantic import ValidationError

PRODUCT_ID = UUID("11111111-1111-4111-8111-111111111111")
QUOTE_ID = UUID("77777777-7777-4777-8777-777777777777")


def proposal_payload() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "headline": "Galician wines for specialised retail",
        "executive_summary": "A focused two-style selection.",
        "product_positioning": [
            {"product_id": str(PRODUCT_ID), "positioning": "Fresh Atlantic style."}
        ],
        "next_steps": ["Review the proposal."],
        "open_questions": [],
        "warnings": ["Human review is required."],
    }


def email_payload() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "subject": "Draft proposal for review",
        "introduction": "Thank you for your inquiry.",
        "recommendation_summary": "We prepared a focused selection.",
        "next_step": "Please review the proposal.",
        "questions": [],
        "closing": "Kind regards",
        "warnings": ["Human review is required before sending."],
    }


def test_versioned_prompts_are_packaged_and_restrict_authoritative_content() -> None:
    proposal = load_proposal_writer_prompt().lower()
    email = load_email_writer_prompt().lower()
    assert "return exactly one json object" in proposal
    assert "return exactly one json object" in email
    assert "price" in proposal and "discount" in proposal
    assert "amount" in email and "stock" in email
    assert "human review" in proposal and "human review" in email


def test_narrative_schemas_accept_valid_payloads_and_forbid_extras() -> None:
    assert ProposalNarrative.model_validate(proposal_payload()).schema_version == "1.0"
    assert EmailDraftNarrative.model_validate(email_payload()).subject

    invalid_proposal = proposal_payload()
    invalid_proposal["subtotal_cents"] = 100
    with pytest.raises(ValidationError):
        ProposalNarrative.model_validate(invalid_proposal)

    invalid_email = email_payload()
    invalid_email["discount"] = "10%"
    with pytest.raises(ValidationError):
        EmailDraftNarrative.model_validate(invalid_email)


def test_proposal_rejects_duplicate_products() -> None:
    payload = proposal_payload()
    positioning = payload["product_positioning"]
    assert isinstance(positioning, list)
    positioning.append(dict(positioning[0]))
    with pytest.raises(ValidationError, match="must be unique"):
        ProposalNarrative.model_validate(payload)


def test_quote_schemas_enforce_exact_arithmetic() -> None:
    item = CalculatedQuoteItem(
        product_id=PRODUCT_ID,
        sku="ADA-ALB-JOV-2025",
        name="Brétema Albariño 2025",
        quantity_bottles=300,
        units_per_case=6,
        cases=50,
        unit_price_cents=840,
        line_total_cents=252000,
    )
    quote = CalculatedQuote(
        agent_run_id=QUOTE_ID,
        items=[item],
        subtotal_cents=252000,
    )
    assert quote.assumptions.stock_reserved is False
    with pytest.raises(ValidationError, match="sum of line totals"):
        CalculatedQuote(
            agent_run_id=QUOTE_ID,
            items=[item],
            subtotal_cents=1,
        )


def test_artifact_quote_snapshot_rejects_inconsistent_total() -> None:
    line = ArtifactQuoteLine(
        product_id=PRODUCT_ID,
        sku="ADA-ALB-JOV-2025",
        name="Brétema Albariño 2025",
        quantity_bottles=300,
        cases=50,
        unit_price_cents=840,
        line_total_cents=252000,
    )
    with pytest.raises(ValidationError, match="sum of line totals"):
        ArtifactQuoteSnapshot(
            quote_id=QUOTE_ID,
            subtotal_cents=1,
            status="draft",
            lines=[line],
            assumptions=QuoteAssumptions(),
        )
