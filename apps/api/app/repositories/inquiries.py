"""Persistence operations for commercial inquiries."""

from __future__ import annotations

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
