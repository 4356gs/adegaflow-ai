"""Validated input and output contracts for Sprint 2 read tools."""

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.domain.enums import MemoryCategory
from app.domain.schemas import (
    CustomerMemoryRecord,
    CustomerRecord,
    OpportunitySummaryRecord,
    ProductRecord,
)


class SearchCatalogInput(BaseModel):
    query: str = Field(min_length=1, max_length=200)
    market: str | None = Field(default=None, min_length=2, max_length=2)
    channel: str | None = Field(default=None, min_length=1, max_length=80)
    max_unit_price_cents: int | None = Field(default=None, ge=0)
    limit: int = Field(default=5, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def strip_query(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("query must contain non-whitespace characters")
        return stripped

    @field_validator("market")
    @classmethod
    def normalize_market(cls, value: str | None) -> str | None:
        return value.upper() if value else None

    @field_validator("channel")
    @classmethod
    def normalize_channel(cls, value: str | None) -> str | None:
        return value.strip().casefold() if value else None


class CatalogCandidate(BaseModel):
    product_id: str
    sku: str
    name: str
    category: str
    price_cents: int = Field(ge=0)
    match_reasons: list[str]


class SearchCatalogData(BaseModel):
    items: list[CatalogCandidate]
    count: int = Field(ge=0)


class ProductDetailsInput(BaseModel):
    product_ids: Annotated[list[UUID], Field(min_length=1, max_length=20)]

    @field_validator("product_ids")
    @classmethod
    def unique_product_ids(cls, values: list[UUID]) -> list[UUID]:
        return list(dict.fromkeys(values))


class ProductDetailsData(BaseModel):
    products: list[ProductRecord]
    missing_product_ids: list[str]


class StockItemInput(BaseModel):
    product_id: UUID
    requested_bottles: int = Field(gt=0, le=1_000_000)


class CheckStockInput(BaseModel):
    items: Annotated[list[StockItemInput], Field(min_length=1, max_length=20)]

    @model_validator(mode="after")
    def reject_duplicate_products(self) -> "CheckStockInput":
        product_ids = [item.product_id for item in self.items]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("items must not contain duplicate product_id values")
        return self


class StockItemResult(BaseModel):
    product_id: str
    requested_bottles: int = Field(gt=0)
    sellable_bottles: int = Field(ge=0)
    available: bool
    shortfall: int = Field(ge=0)


class CheckStockData(BaseModel):
    items: list[StockItemResult]


class RetrieveCustomerHistoryInput(BaseModel):
    customer_id: UUID
    categories: list[MemoryCategory] | None = None
    limit: int = Field(default=20, ge=1, le=100)

    @field_validator("categories")
    @classmethod
    def unique_categories(
        cls,
        values: list[MemoryCategory] | None,
    ) -> list[MemoryCategory] | None:
        return list(dict.fromkeys(values)) if values else values


class CustomerHistoryData(BaseModel):
    customer: CustomerRecord
    memories: list[CustomerMemoryRecord]
    opportunities: list[OpportunitySummaryRecord]
