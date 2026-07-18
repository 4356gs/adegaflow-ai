from datetime import UTC, datetime
from uuid import UUID

import pytest
from app.domain.analysis import InquiryAnalysis, InquiryIntent
from app.domain.enums import MemoryCategory, OpportunityPriority
from app.domain.internal_actions import (
    MemoryActionInput,
    MemoryFactInput,
    OpportunityActionInput,
    canonical_fingerprint,
    priority_for_score,
)
from app.services.opportunity_qualification import (
    MemoryExtractionService,
    qualification_score,
)
from pydantic import ValidationError


def test_priority_thresholds() -> None:
    assert priority_for_score(0) is OpportunityPriority.LOW
    assert priority_for_score(49) is OpportunityPriority.LOW
    assert priority_for_score(50) is OpportunityPriority.MEDIUM
    assert priority_for_score(74) is OpportunityPriority.MEDIUM
    assert priority_for_score(75) is OpportunityPriority.HIGH
    assert priority_for_score(100) is OpportunityPriority.HIGH


@pytest.mark.parametrize(
    ("intent", "expected"),
    [
        (InquiryIntent.B2B_PURCHASE_INQUIRY, 60),
        (InquiryIntent.PRICE_REQUEST, 50),
        (InquiryIntent.SAMPLE_REQUEST, 50),
        (InquiryIntent.PRODUCT_INFORMATION, 40),
        (InquiryIntent.OTHER, 30),
    ],
)
def test_score_for_each_supported_intent(
    intent: InquiryIntent, expected: int
) -> None:
    analysis = InquiryAnalysis(
        language="en",
        intent=intent,
        market="DE",
        company_name="Buyer GmbH",
    )
    assert qualification_score(analysis, customer_resolved=False) == expected


def test_opportunity_priority_must_match_score() -> None:
    with pytest.raises(ValidationError):
        OpportunityActionInput(
            inquiry_id=UUID("dddddddd-dddd-4ddd-8ddd-ddddddddddd1"),
            customer_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1"),
            title="Buyer — DE — 600 bottles",
            priority=OpportunityPriority.LOW,
            score=90,
            market="DE",
            summary="Validated opportunity.",
            idempotency_key="run:create_crm_opportunity",
        )


def test_memory_payload_is_normalized_sorted_and_fingerprinted() -> None:
    payload = MemoryActionInput(
        customer_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1"),
        source_inquiry_id=UUID("dddddddd-dddd-4ddd-8ddd-ddddddddddd1"),
        memories=[
            MemoryFactInput(
                category=MemoryCategory.PREFERENCE,
                content="  Market:   DE. ",
            ),
            MemoryFactInput(
                category=MemoryCategory.PREFERENCE,
                content="market: de.",
            ),
            MemoryFactInput(
                category=MemoryCategory.INTERACTION,
                content="Samples requested.",
            ),
        ],
        idempotency_key="run:save_customer_memory",
    )
    assert len(payload.memories) == 2
    assert canonical_fingerprint(payload) == canonical_fingerprint(
        MemoryActionInput.model_validate(payload.model_dump(mode="json"))
    )
    assert datetime.now(UTC).tzinfo is not None


def test_memory_extraction_excludes_sensitive_fields_and_is_limited() -> None:
    analysis = InquiryAnalysis(
        language="en",
        intent=InquiryIntent.SAMPLE_REQUEST,
        market="DE",
        product_interest=[f"Wine {index}" for index in range(10)],
        channel="specialty_retail",
        samples_requested=True,
        price_list_requested=True,
        budget_total_cents=900_000,
        budget_currency="EUR",
        sample_delivery_address="Private Street 1",
        tax_identifier="SECRET-TAX-ID",
        contact_email="private@example.test",
        certification_requirements=[f"Cert {index}" for index in range(20)],
    )

    facts = MemoryExtractionService().build(analysis)

    assert len(facts) == 20
    content = " ".join(fact.content for fact in facts)
    assert "Private Street" not in content
    assert "SECRET-TAX-ID" not in content
    assert "private@example.test" not in content
    assert "900000" not in content
