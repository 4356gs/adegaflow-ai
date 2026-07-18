"""Strict narrative contracts for generated commercial artifacts."""

from __future__ import annotations

from typing import Final, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.domain.quote import QuoteAssumptions

ARTIFACT_NARRATIVE_SCHEMA_VERSION: Final[Literal["1.0"]] = "1.0"
MAX_LIST_ITEM_LENGTH: Final = 500
ALLOWED_PROPOSAL_NEXT_STEPS: Final = (
    "Review the draft proposal and confirm the missing commercial details.",
)
ALLOWED_EMAIL_NEXT_STEPS: Final = (
    "Review the proposal and reply with any missing commercial details.",
)


def _normalize_text_list(values: list[str]) -> list[str]:
    normalized = [value.strip() for value in values if value.strip()]
    if any(len(value) > MAX_LIST_ITEM_LENGTH for value in normalized):
        raise ValueError(
            f"List items must not exceed {MAX_LIST_ITEM_LENGTH} characters."
        )
    return list(dict.fromkeys(normalized))


class StrictArtifactNarrativeModel(BaseModel):
    """Reject undeclared fields and strip surrounding text whitespace."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ProposalProductPositioning(StrictArtifactNarrativeModel):
    """Narrative positioning for one authoritative product identifier."""

    product_id: UUID
    positioning: str = Field(min_length=1, max_length=1_000)


class ProposalNarrative(StrictArtifactNarrativeModel):
    """Model-owned narrative sections of a proposal draft."""

    schema_version: Literal["1.0"] = ARTIFACT_NARRATIVE_SCHEMA_VERSION
    headline: str = Field(min_length=1, max_length=200)
    executive_summary: str = Field(min_length=1, max_length=2_000)
    product_positioning: list[ProposalProductPositioning] = Field(
        min_length=1,
        max_length=20,
    )
    next_steps: list[str] = Field(default_factory=list, max_length=20)
    open_questions: list[str] = Field(default_factory=list, max_length=20)
    warnings: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("next_steps", "open_questions", "warnings")
    @classmethod
    def normalize_text_lists(cls, values: list[str]) -> list[str]:
        return _normalize_text_list(values)

    @model_validator(mode="after")
    def ensure_unique_products(self) -> ProposalNarrative:
        product_ids = [item.product_id for item in self.product_positioning]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("Proposal product IDs must be unique.")
        return self


class EmailDraftNarrative(StrictArtifactNarrativeModel):
    """Model-owned narrative sections of an email draft."""

    schema_version: Literal["1.0"] = ARTIFACT_NARRATIVE_SCHEMA_VERSION
    subject: str = Field(min_length=1, max_length=200)
    introduction: str = Field(min_length=1, max_length=1_500)
    recommendation_summary: str = Field(min_length=1, max_length=2_000)
    next_step: str = Field(min_length=1, max_length=500)
    questions: list[str] = Field(default_factory=list, max_length=20)
    closing: str = Field(min_length=1, max_length=500)
    warnings: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("questions", "warnings")
    @classmethod
    def normalize_text_lists(cls, values: list[str]) -> list[str]:
        return _normalize_text_list(values)


class ArtifactBuyerSnapshot(StrictArtifactNarrativeModel):
    """Buyer data known when an artifact is assembled."""

    company_name: str | None = Field(default=None, max_length=160)
    contact_name: str | None = Field(default=None, max_length=160)
    email: str | None = Field(default=None, max_length=320)
    market: str | None = Field(
        default=None,
        min_length=2,
        max_length=2,
        pattern=r"^[A-Z]{2}$",
    )
    country_code: str | None = Field(
        default=None,
        min_length=2,
        max_length=2,
        pattern=r"^[A-Z]{2}$",
    )


class ArtifactQuoteLine(StrictArtifactNarrativeModel):
    """One authoritative quote line embedded in an artifact snapshot."""

    product_id: UUID
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=160)
    quantity_bottles: int = Field(gt=0, le=1_000_000)
    cases: int = Field(gt=0, le=1_000_000)
    unit_price_cents: int = Field(ge=0)
    line_total_cents: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_line_total(self) -> ArtifactQuoteLine:
        expected = self.quantity_bottles * self.unit_price_cents
        if self.line_total_cents != expected:
            raise ValueError(
                "line_total_cents must equal quantity_bottles "
                "* unit_price_cents."
            )
        return self


class ArtifactQuoteSnapshot(StrictArtifactNarrativeModel):
    """Validated immutable commercial snapshot used by a proposal."""

    quote_id: UUID
    currency: Literal["EUR"] = "EUR"
    subtotal_cents: int = Field(ge=0)
    status: Literal["draft", "reviewed"]
    lines: list[ArtifactQuoteLine] = Field(min_length=1, max_length=20)
    assumptions: QuoteAssumptions

    @model_validator(mode="after")
    def validate_quote_integrity(self) -> ArtifactQuoteSnapshot:
        product_ids = [line.product_id for line in self.lines]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("Artifact quote product IDs must be unique.")
        if self.subtotal_cents != sum(
            line.line_total_cents for line in self.lines
        ):
            raise ValueError(
                "subtotal_cents must equal the sum of line totals."
            )
        return self


class ProposalArtifactContent(StrictArtifactNarrativeModel):
    """Complete proposal content persisted for human review."""

    schema_version: Literal["1.0"] = ARTIFACT_NARRATIVE_SCHEMA_VERSION
    artifact_type: Literal["proposal"] = "proposal"
    language: str = Field(
        min_length=2,
        max_length=2,
        pattern=r"^[a-z]{2}$",
    )
    buyer: ArtifactBuyerSnapshot
    quote: ArtifactQuoteSnapshot
    narrative: ProposalNarrative
    review_status: Literal["needs_review"] = "needs_review"


class EmailCommercialBlock(StrictArtifactNarrativeModel):
    """Authoritative quote data embedded in an email draft artifact."""

    quote_id: UUID
    currency: Literal["EUR"] = "EUR"
    subtotal_cents: int = Field(ge=0)
    status: Literal["draft", "reviewed"]
    lines: list[ArtifactQuoteLine] = Field(min_length=1, max_length=20)
    assumptions: QuoteAssumptions

    @model_validator(mode="after")
    def validate_commercial_block(self) -> EmailCommercialBlock:
        product_ids = [line.product_id for line in self.lines]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("Email quote product IDs must be unique.")
        if self.subtotal_cents != sum(
            line.line_total_cents for line in self.lines
        ):
            raise ValueError(
                "subtotal_cents must equal the sum of line totals."
            )
        return self


class EmailDraftArtifactContent(StrictArtifactNarrativeModel):
    """Complete email draft content persisted for human review."""

    schema_version: Literal["1.0"] = ARTIFACT_NARRATIVE_SCHEMA_VERSION
    artifact_type: Literal["email_draft"] = "email_draft"
    language: str = Field(
        min_length=2,
        max_length=2,
        pattern=r"^[a-z]{2}$",
    )
    recipient: ArtifactBuyerSnapshot
    proposal_artifact_id: UUID
    commercial_block: EmailCommercialBlock
    narrative: EmailDraftNarrative
    review_status: Literal["needs_review"] = "needs_review"
