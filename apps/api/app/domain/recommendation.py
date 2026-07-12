"""Contracts for model drafts and deterministically validated recommendations."""

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

from app.domain.schemas import ProductRecord

RECOMMENDATION_SCHEMA_VERSION: Final[Literal["1.0"]] = "1.0"


class StrictRecommendationModel(BaseModel):
    """Reject undeclared fields in recommendation-domain payloads."""

    model_config = ConfigDict(extra="forbid")


class RecommendationDraftItem(StrictRecommendationModel):
    """Non-authoritative product choice returned by the model."""

    product_id: UUID
    quantity_bottles: int = Field(gt=0, le=1_000_000)
    rationale: str = Field(min_length=1, max_length=1_000)

    @field_validator("rationale")
    @classmethod
    def strip_rationale(cls, value: str) -> str:
        return value.strip()


class RecommendationDraft(StrictRecommendationModel):
    """Model-owned fields accepted before deterministic validation."""

    schema_version: Literal["1.0"] = RECOMMENDATION_SCHEMA_VERSION
    items: list[RecommendationDraftItem] = Field(
        min_length=1,
        max_length=20,
    )
    summary: str = Field(min_length=1, max_length=2_000)
    warnings: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("summary")
    @classmethod
    def strip_summary(cls, value: str) -> str:
        return value.strip()

    @field_validator("warnings")
    @classmethod
    def normalize_warnings(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values if value.strip()]
        return list(dict.fromkeys(normalized))


class RecommendationContext(StrictRecommendationModel):
    """Validated commercial requirements applied by the backend."""

    market: str | None = Field(default=None, min_length=2, max_length=2)
    channel: str | None = Field(default=None, min_length=1, max_length=80)
    product_interest: str | None = Field(
        default=None,
        min_length=1,
        max_length=160,
    )
    estimated_bottles: int | None = Field(default=None, gt=0)
    requested_references: int | None = Field(
        default=None,
        ge=1,
        le=20,
    )
    required_certifications: list[str] = Field(
        default_factory=list,
        max_length=20,
    )
    budget_total_cents: int | None = Field(default=None, ge=0)
    budget_currency: str | None = Field(
        default=None,
        min_length=3,
        max_length=3,
    )

    @field_validator("market")
    @classmethod
    def normalize_market(
        cls,
        value: str | None,
    ) -> str | None:
        return value.upper() if value else None

    @field_validator("channel")
    @classmethod
    def normalize_channel(
        cls,
        value: str | None,
    ) -> str | None:
        return value.strip().casefold() if value else None

    @field_validator("product_interest")
    @classmethod
    def normalize_product_interest(
        cls,
        value: str | None,
    ) -> str | None:
        return value.strip() if value else None

    @field_validator("required_certifications")
    @classmethod
    def normalize_certifications(
        cls,
        values: list[str],
    ) -> list[str]:
        normalized = [value.strip() for value in values if value.strip()]
        return list(dict.fromkeys(normalized))

    @field_validator("budget_currency")
    @classmethod
    def normalize_currency(
        cls,
        value: str | None,
    ) -> str | None:
        return value.upper() if value else None


class StockEvidence(StrictRecommendationModel):
    """Authoritative stock observation produced by check_stock."""

    product_id: UUID
    requested_bottles: int = Field(gt=0)
    sellable_bottles: int = Field(ge=0)
    available: bool
    shortfall: int = Field(ge=0)


class RecommendationEvidence(StrictRecommendationModel):
    """Authoritative catalog and stock evidence collected during one run."""

    retrieved_product_ids: list[UUID] = Field(
        default_factory=list,
        max_length=100,
    )
    products: list[ProductRecord] = Field(
        default_factory=list,
        max_length=100,
    )
    stock_items: list[StockEvidence] = Field(
        default_factory=list,
        max_length=100,
    )

    @field_validator("retrieved_product_ids")
    @classmethod
    def unique_retrieved_ids(
        cls,
        values: list[UUID],
    ) -> list[UUID]:
        return list(dict.fromkeys(values))

    @field_validator("products")
    @classmethod
    def product_ids_must_be_uuids(
        cls,
        values: list[ProductRecord],
    ) -> list[ProductRecord]:
        for product in values:
            UUID(product.id)
        return values


class RecommendationValidationIssue(StrictRecommendationModel):
    """One machine-readable rule violation."""

    code: str = Field(min_length=1, max_length=80)
    path: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=500)
    correctable: bool
    product_id: UUID | None = None


class ValidatedRecommendationItem(StrictRecommendationModel):
    """Product line enriched only from authoritative evidence."""

    product_id: UUID
    sku: str
    name: str
    quantity_bottles: int = Field(gt=0)
    units_per_case: int = Field(gt=0)
    cases: int = Field(gt=0)
    unit_price_cents: int = Field(ge=0)
    sellable_bottles: int = Field(ge=0)
    certifications: list[str]
    rationale: str


class ValidatedRecommendation(StrictRecommendationModel):
    """Persistable recommendation result without quote calculations."""

    schema_version: Literal["1.0"] = RECOMMENDATION_SCHEMA_VERSION
    items: list[ValidatedRecommendationItem] = Field(
        min_length=1,
        max_length=20,
    )
    total_bottles: int = Field(gt=0)
    currency: Literal["EUR"] = "EUR"
    summary: str
    warnings: list[str]
    validation_status: Literal["valid"] = "valid"


class RecommendationValidationOutcome(StrictRecommendationModel):
    """Validation result suitable for completion or one correction round."""

    valid: bool
    result: ValidatedRecommendation | None
    issues: list[RecommendationValidationIssue]

    @model_validator(mode="after")
    def ensure_consistent_outcome(
        self,
    ) -> RecommendationValidationOutcome:
        if self.valid and (self.result is None or self.issues):
            raise ValueError(
                "A valid outcome requires a result and no issues."
            )
        if not self.valid and self.result is not None:
            raise ValueError(
                "An invalid outcome cannot contain a validated result."
            )
        return self

    def correction_payload(self) -> dict[str, object]:
        """Return only structured errors safe to send for one correction."""

        return {
            "errors": [
                issue.model_dump(mode="json")
                for issue in self.issues
                if issue.correctable
            ]
        }
