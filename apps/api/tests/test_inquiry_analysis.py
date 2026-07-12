from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

import pytest
from app.ai.prompts import INQUIRY_ANALYSIS_PROMPT_VERSION, load_inquiry_analysis_prompt
from app.ai.schemas import ModelTurn, QwenErrorInfo
from app.db.models import Inquiry
from app.domain.analysis import InquiryAnalysis, InquiryIntent, compute_missing_fields
from app.services.inquiry_analysis import InquiryAnalysisError, InquiryAnalysisService
from pydantic import BaseModel
from sqlalchemy.orm import Session

PRIMARY_INQUIRY_ID = UUID("ffffffff-ffff-4fff-8fff-fffffffffff1")
INVALID_INQUIRY_ID = UUID("ffffffff-ffff-4fff-8fff-fffffffffff2")
PROVIDER_ERROR_INQUIRY_ID = UUID("ffffffff-ffff-4fff-8fff-fffffffffff3")

PRIMARY_MESSAGE = """Hello,

We are evaluating Galician Albariño for distribution through specialised wine shops
in Germany. For the initial launch, we estimate approximately 600 bottles and
would like delivery within the next 60 days.

Please send us your price list and recommend two suitable references. We would
also like to receive samples before making a final decision.

Best regards,
Anna Keller
Rhein Selection GmbH
"""

PRIMARY_PAYLOAD: dict[str, Any] = {
    "schema_version": "1.0",
    "language": "EN",
    "intent": "b2b_purchase_inquiry",
    "market": "de",
    "product_interest": [" Albariño ", "albariño"],
    "estimated_bottles": 600,
    "channel": "specialty_retail",
    "target_horizon_days": 60,
    "target_date": None,
    "samples_requested": True,
    "price_list_requested": True,
    "budget_total_cents": None,
    "budget_currency": None,
    "sample_delivery_address": None,
    "delivery_terms": None,
    "certification_requirements": [],
    "tax_identifier": None,
    "company_name": "Rhein Selection GmbH",
    "contact_name": "Anna Keller",
    "contact_email": None,
}


class FakeJsonClient:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.messages: Sequence[dict[str, Any]] | None = None

    def complete_json(
        self,
        messages: Sequence[dict[str, Any]],
        *,
        schema: type[BaseModel] | None = None,
        model: str | None = None,
        temperature: float = 0.1,
    ) -> tuple[dict[str, Any], ModelTurn]:
        self.messages = messages
        return self.payload, ModelTurn(model="fake-qwen")


class FakeProviderError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("provider failed")
        self.info = QwenErrorInfo(
            code="QWEN_TIMEOUT",
            message="Qwen Cloud did not respond before the timeout.",
            retryable=True,
            category="timeout",
        )


class FailingJsonClient:
    def complete_json(
        self,
        messages: Sequence[dict[str, Any]],
        *,
        schema: type[BaseModel] | None = None,
        model: str | None = None,
        temperature: float = 0.1,
    ) -> tuple[dict[str, Any], ModelTurn]:
        raise FakeProviderError


def add_inquiry(session: Session, inquiry_id: UUID, message: str = PRIMARY_MESSAGE) -> None:
    session.add(
        Inquiry(
            id=str(inquiry_id),
            customer_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1",
            source="demo",
            raw_message=message,
            detected_language=None,
            status="new",
            extracted_data={},
            missing_fields=[],
        )
    )
    session.commit()


def test_primary_inquiry_analysis_is_persisted(db_session: Session) -> None:
    add_inquiry(db_session, PRIMARY_INQUIRY_ID)
    client = FakeJsonClient(PRIMARY_PAYLOAD)

    result = InquiryAnalysisService(db_session, client).analyze(PRIMARY_INQUIRY_ID)

    assert result.prompt_version == INQUIRY_ANALYSIS_PROMPT_VERSION
    assert result.analysis.language == "en"
    assert result.analysis.market == "DE"
    assert result.analysis.product_interest == ["Albariño"]
    assert result.missing_fields == [
        "target_date",
        "budget",
        "delivery_terms",
        "certification_requirements",
        "tax_identifier",
        "sample_delivery_address",
    ]

    persisted = db_session.get(Inquiry, str(PRIMARY_INQUIRY_ID))
    assert persisted is not None
    assert persisted.status == "completed"
    assert persisted.detected_language == "en"
    assert persisted.extracted_data["estimated_bottles"] == 600
    assert persisted.missing_fields == result.missing_fields
    assert client.messages is not None
    assert "Do not return `missing_fields`" in str(client.messages[0]["content"])


def test_missing_fields_are_computed_deterministically() -> None:
    analysis = InquiryAnalysis(
        language="es",
        intent=InquiryIntent.B2B_PURCHASE_INQUIRY,
        market=None,
        product_interest=[],
        samples_requested=False,
    )

    assert compute_missing_fields(analysis) == [
        "market",
        "product_interest",
        "estimated_bottles",
        "channel",
        "target_date",
        "budget",
        "delivery_terms",
        "certification_requirements",
        "tax_identifier",
    ]


def test_product_information_has_minimal_required_fields() -> None:
    analysis = InquiryAnalysis(
        language="en",
        intent=InquiryIntent.PRODUCT_INFORMATION,
        market="DE",
        product_interest=["Albariño"],
    )

    assert compute_missing_fields(analysis) == []


def test_invalid_payload_marks_inquiry_failed(db_session: Session) -> None:
    add_inquiry(db_session, INVALID_INQUIRY_ID)
    payload = dict(PRIMARY_PAYLOAD)
    payload["estimated_bottles"] = 0

    with pytest.raises(InquiryAnalysisError) as error:
        InquiryAnalysisService(db_session, FakeJsonClient(payload)).analyze(
            INVALID_INQUIRY_ID
        )

    assert error.value.code == "MODEL_INVALID_JSON"
    persisted = db_session.get(Inquiry, str(INVALID_INQUIRY_ID))
    assert persisted is not None
    assert persisted.status == "failed"
    assert persisted.extracted_data == {}


def test_provider_error_marks_inquiry_failed(db_session: Session) -> None:
    add_inquiry(db_session, PROVIDER_ERROR_INQUIRY_ID)

    with pytest.raises(InquiryAnalysisError) as error:
        InquiryAnalysisService(db_session, FailingJsonClient()).analyze(
            PROVIDER_ERROR_INQUIRY_ID
        )

    assert error.value.code == "QWEN_TIMEOUT"
    assert error.value.retryable is True
    persisted = db_session.get(Inquiry, str(PROVIDER_ERROR_INQUIRY_ID))
    assert persisted is not None
    assert persisted.status == "failed"


def test_unknown_inquiry_returns_safe_error(db_session: Session) -> None:
    with pytest.raises(InquiryAnalysisError) as error:
        InquiryAnalysisService(db_session, FakeJsonClient(PRIMARY_PAYLOAD)).analyze(
            UUID("99999999-9999-4999-8999-999999999999")
        )

    assert error.value.code == "INQUIRY_NOT_FOUND"
    assert error.value.retryable is False


def test_versioned_prompt_is_packaged() -> None:
    prompt = load_inquiry_analysis_prompt()

    assert "Inquiry analysis prompt — v1" in prompt
    assert "Return exactly one JSON object" in prompt
