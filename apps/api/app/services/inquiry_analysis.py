"""Structured inquiry-analysis application service."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.ai.prompts import INQUIRY_ANALYSIS_PROMPT_VERSION, load_inquiry_analysis_prompt
from app.ai.schemas import ModelTurn
from app.domain.analysis import InquiryAnalysis, InquiryAnalysisResult, compute_missing_fields
from app.repositories.inquiries import InquiryRepository

Message = dict[str, Any]


class JsonCompletionClient(Protocol):
    """Provider-neutral protocol required by the analysis service."""

    def complete_json(
        self,
        messages: Sequence[Message],
        *,
        schema: type[BaseModel] | None = None,
        model: str | None = None,
        temperature: float = 0.1,
    ) -> tuple[dict[str, Any], ModelTurn]: ...


class InquiryAnalysisError(RuntimeError):
    """Safe application error for failed inquiry analysis."""

    def __init__(self, *, code: str, message: str, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


def _safe_provider_error(exc: Exception) -> InquiryAnalysisError:
    info = getattr(exc, "info", None)
    provider_code = getattr(info, "code", None)
    provider_message = getattr(info, "message", None)
    retryable = bool(getattr(info, "retryable", False))

    if provider_code == "QWEN_INVALID_RESPONSE":
        return InquiryAnalysisError(
            code="MODEL_INVALID_JSON",
            message="The model response did not conform to the inquiry schema.",
            retryable=True,
        )

    if isinstance(provider_code, str) and isinstance(provider_message, str):
        return InquiryAnalysisError(
            code=provider_code,
            message=provider_message,
            retryable=retryable,
        )

    return InquiryAnalysisError(
        code="MODEL_ANALYSIS_FAILED",
        message="The inquiry could not be analyzed.",
        retryable=False,
    )


class InquiryAnalysisService:
    """Analyze one persisted inquiry and store only validated structured data."""

    def __init__(
        self,
        session: Session,
        client: JsonCompletionClient,
    ) -> None:
        self.session = session
        self.client = client
        self.repository = InquiryRepository(session)

    def analyze(self, inquiry_id: UUID | str) -> InquiryAnalysisResult:
        normalized_id = str(inquiry_id)
        inquiry = self.repository.get_by_id(normalized_id)
        if inquiry is None:
            raise InquiryAnalysisError(
                code="INQUIRY_NOT_FOUND",
                message="The requested inquiry does not exist.",
                retryable=False,
            )

        self.repository.mark_processing(inquiry)
        self.session.commit()

        messages: list[Message] = [
            {
                "role": "system",
                "content": load_inquiry_analysis_prompt(),
            },
            {
                "role": "user",
                "content": (
                    "Analyze this commercial inquiry and return the required JSON object:\n\n"
                    + inquiry.raw_message
                ),
            },
        ]

        try:
            payload, turn = self.client.complete_json(
                messages,
                schema=InquiryAnalysis,
                temperature=0.0,
            )
            analysis = InquiryAnalysis.model_validate(payload)
            missing_fields = compute_missing_fields(analysis)
        except ValidationError as exc:
            self._mark_failed(normalized_id)
            raise InquiryAnalysisError(
                code="MODEL_INVALID_JSON",
                message="The model response did not conform to the inquiry schema.",
                retryable=True,
            ) from exc
        except Exception as exc:
            self._mark_failed(normalized_id)
            raise _safe_provider_error(exc) from exc

        refreshed = self.repository.get_by_id(normalized_id)
        if refreshed is None:
            raise InquiryAnalysisError(
                code="INQUIRY_NOT_FOUND",
                message="The inquiry was removed during analysis.",
                retryable=False,
            )

        self.repository.save_analysis(refreshed, analysis, missing_fields)
        self.session.commit()

        return InquiryAnalysisResult(
            inquiry_id=UUID(normalized_id),
            analysis=analysis,
            missing_fields=missing_fields,
            model=turn.model,
            prompt_version=INQUIRY_ANALYSIS_PROMPT_VERSION,
        )

    def _mark_failed(self, inquiry_id: str) -> None:
        self.session.rollback()
        inquiry = self.repository.get_by_id(inquiry_id)
        if inquiry is None:
            return
        self.repository.mark_failed(inquiry)
        self.session.commit()
