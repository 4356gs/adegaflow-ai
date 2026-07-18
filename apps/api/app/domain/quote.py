"""Strict contracts for deterministic quote calculation."""

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

QUOTE_SCHEMA_VERSION: Final[Literal["1.0"]] = "1.0"


class StrictQuoteModel(BaseModel):
    """Reject undeclared fields in quote-domain payloads."""

    model_config = ConfigDict(extra="forbid")


class CalculateQuoteRequest(StrictQuoteModel):
    """Logical input accepted by the deterministic quote service."""

    agent_run_id: UUID


class QuoteAssumptions(StrictQuoteModel):
    """Visible commercial assumptions persisted with every quote."""

    schema_version: Literal["1.0"] = QUOTE_SCHEMA_VERSION
    unit_price_source: Literal[
        "validated_recommendation_snapshot"
    ] = "validated_recommendation_snapshot"
    taxes_included: Literal[False] = False
    transport_included: Literal[False] = False
    insurance_included: Literal[False] = False
    duties_and_customs_included: Literal[False] = False
    stock_reserved: Literal[False] = False
    human_review_required: Literal[True] = True


class CalculatedQuoteItem(StrictQuoteModel):
    """One quote line calculated only from validated recommendation data."""

    product_id: UUID
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=160)
    quantity_bottles: int = Field(gt=0, le=1_000_000)
    units_per_case: int = Field(gt=0)
    cases: int = Field(gt=0)
    unit_price_cents: int = Field(ge=0)
    line_total_cents: int = Field(ge=0)

    @field_validator("sku", "name")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_calculations(self) -> CalculatedQuoteItem:
        if self.quantity_bottles % self.units_per_case != 0:
            raise ValueError(
                "quantity_bottles must be divisible by units_per_case."
            )

        expected_cases = self.quantity_bottles // self.units_per_case
        if self.cases != expected_cases:
            raise ValueError(
                "cases must equal quantity_bottles // units_per_case."
            )

        expected_total = (
            self.quantity_bottles * self.unit_price_cents
        )
        if self.line_total_cents != expected_total:
            raise ValueError(
                "line_total_cents must equal quantity_bottles "
                "* unit_price_cents."
            )

        return self


class CalculatedQuote(StrictQuoteModel):
    """Complete deterministic quote before persistence."""

    schema_version: Literal["1.0"] = QUOTE_SCHEMA_VERSION
    agent_run_id: UUID
    currency: Literal["EUR"] = "EUR"
    items: list[CalculatedQuoteItem] = Field(
        min_length=1,
        max_length=20,
    )
    subtotal_cents: int = Field(ge=0)
    budget_total_cents: int | None = Field(default=None, ge=0)
    budget_exceeded: bool = False
    warnings: list[str] = Field(default_factory=list, max_length=20)
    assumptions: QuoteAssumptions = Field(
        default_factory=QuoteAssumptions
    )

    @field_validator("warnings")
    @classmethod
    def normalize_warnings(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values if value.strip()]
        return list(dict.fromkeys(normalized))

    @model_validator(mode="after")
    def validate_quote(self) -> CalculatedQuote:
        product_ids = [item.product_id for item in self.items]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("Quote product IDs must be unique.")

        expected_subtotal = sum(
            item.line_total_cents for item in self.items
        )
        if self.subtotal_cents != expected_subtotal:
            raise ValueError(
                "subtotal_cents must equal the sum of line totals."
            )

        expected_budget_exceeded = (
            self.budget_total_cents is not None
            and self.subtotal_cents > self.budget_total_cents
        )
        if self.budget_exceeded != expected_budget_exceeded:
            raise ValueError(
                "budget_exceeded does not match subtotal and budget."
            )

        return self