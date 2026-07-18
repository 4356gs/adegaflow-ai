"""Persistence operations for commercial inquiries."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Inquiry
from app.domain.analysis import InquiryAnalysis
from app.domain.enums import InquiryStatus


class InquiryRepository:
    """Repository boundary used by inquiry-analysis services."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, inquiry_id: str) -> Inquiry | None:
        return self.session.get(Inquiry, inquiry_id)

    def get_by_submission_key(self, submission_key: str) -> Inquiry | None:
        return self.session.scalar(select(Inquiry).where(Inquiry.submission_key == submission_key))

    def create(
        self,
        *,
        source: str,
        raw_message: str,
        customer_id: str | None,
        submission_key: str,
    ) -> Inquiry:
        inquiry = Inquiry(
            id=str(uuid4()),
            source=source,
            raw_message=raw_message,
            customer_id=customer_id,
            submission_key=submission_key,
            status=InquiryStatus.NEW.value,
            extracted_data={},
            missing_fields=[],
        )
        self.session.add(inquiry)
        self.session.flush()
        return inquiry

    def list_inquiries(
        self,
        *,
        status: InquiryStatus | None,
        limit: int,
        offset: int,
    ) -> list[Inquiry]:
        statement = select(Inquiry).order_by(Inquiry.received_at.desc(), Inquiry.id.desc())
        if status is not None:
            statement = statement.where(Inquiry.status == status.value)
        return list(self.session.scalars(statement.offset(offset).limit(limit)))

    def mark_processing(self, inquiry: Inquiry) -> None:
        inquiry.status = InquiryStatus.PROCESSING.value

    def mark_failed(self, inquiry: Inquiry) -> None:
        inquiry.status = InquiryStatus.FAILED.value

    def save_analysis(
        self,
        inquiry: Inquiry,
        analysis: InquiryAnalysis,
        missing_fields: list[str],
    ) -> None:
        inquiry.detected_language = analysis.language
        inquiry.extracted_data = analysis.model_dump(mode="json")
        inquiry.missing_fields = list(missing_fields)
        inquiry.status = InquiryStatus.COMPLETED.value
