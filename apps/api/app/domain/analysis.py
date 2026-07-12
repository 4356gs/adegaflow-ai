"""Structured inquiry-analysis contracts and deterministic business rules."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InquiryIntent(StrEnum):
    """Commercial intent categories supported by the MVP analysis phase."""

    B2B_PURCHASE_INQUIRY = "b2b_purchase_inquiry"
    PRODUCT_INFORMATION = "product_information"
    SAMPLE_REQUEST = "sample_request"
    PRICE_REQUEST = "price_request"
    OTHER = "other"


class InquiryAnalysis(BaseModel):
    """Validated structured extraction produced from one commercial inquiry."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: Literal["1.0"] = "1.0"
    language: str = Field(min_length=2, max_length=2, pattern=r"^[a-z]{2}$")
    intent: InquiryIntent
    market: str | None = Field(
        default=None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$"
    )
    product_interest: list[str] = Field(default_factory=list, max_length=10)
    estimated_bottles: int | None = Field(default=None, gt=0)
    channel: str | None = Field(default=None, max_length=80)
    target_horizon_days: int | None = Field(default=None, ge=0, le=730)
    target_date: date | None = None
    samples_requested: bool = False
    price_list_requested: bool = False
    budget_total_cents: int | None = Field(default=None, ge=0)
    budget_currency: str | None = Field(
        default=None, min_length=3, max_length=3, pattern=r"^[A-Z]{3}$"
    )
    sample_delivery_address: str | None = Field(default=None, max_length=500)
    delivery_terms: str | None = Field(default=None, max_length=160)
    certification_requirements: list[str] = Field(default_factory=list, max_length=20)
    tax_identifier: str | None = Field(default=None, max_length=80)
    company_name: str | None = Field(default=None, max_length=160)
    contact_name: str | None = Field(default=None, max_length=160)
    contact_email: str | None = Field(default=None, max_length=320)

    @field_validator("language", mode="before")
    @classmethod
    def normalize_language(cls, value: object) -> object:
        if isinstance(value, str):
            return value.lower()
        return value

    @field_validator("market", mode="before")
    @classmethod
    def normalize_market(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        normalized = value.upper()
        if not normalized.isalpha():
            raise ValueError("market must be a two-letter country code")
        return normalized

    @field_validator("budget_currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        normalized = value.upper()
        if not normalized.isalpha():
            raise ValueError("budget_currency must be a three-letter currency code")
        return normalized

    @field_validator("product_interest", "certification_requirements")
    @classmethod
    def normalize_string_lists(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for value in values:
            cleaned = value.strip()
            if not cleaned:
                continue
            key = cleaned.casefold()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(cleaned)
        return normalized


class InquiryAnalysisResult(BaseModel):
    """Persisted analysis result returned by the application service."""

    inquiry_id: UUID
    analysis: InquiryAnalysis
    missing_fields: list[str]
    model: str
    prompt_version: str


_PURCHASE_INTENTS = {
    InquiryIntent.B2B_PURCHASE_INQUIRY,
    InquiryIntent.PRICE_REQUEST,
    InquiryIntent.SAMPLE_REQUEST,
}


def compute_missing_fields(analysis: InquiryAnalysis) -> list[str]:
    """Compute clarification needs from validated data, never from model opinion."""

    missing: list[str] = []

    def add(field_name: str, condition: bool) -> None:
        if condition:
            missing.append(field_name)

    add("market", analysis.market is None)
    add("product_interest", not analysis.product_interest)

    if analysis.intent in _PURCHASE_INTENTS:
        add("estimated_bottles", analysis.estimated_bottles is None)
        add("channel", not analysis.channel)
        add("target_date", analysis.target_date is None)
        add("budget", analysis.budget_total_cents is None)
        add("delivery_terms", not analysis.delivery_terms)
        add(
            "certification_requirements",
            not analysis.certification_requirements,
        )
        add("tax_identifier", not analysis.tax_identifier)

    if analysis.samples_requested:
        add("sample_delivery_address", not analysis.sample_delivery_address)

    return missing
