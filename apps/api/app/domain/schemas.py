"""Pydantic schemas for persisted domain records exposed to tools."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import MemoryCategory, OpportunityPriority, OpportunityStage


class ProductRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sku: str
    name: str
    category: str
    variety: str
    vintage: int | None
    description: str
    price_cents: int = Field(ge=0)
    units_per_case: int = Field(gt=0)
    recommended_markets: list[str]
    recommended_channels: list[str]
    tasting_notes: str | None
    certifications: list[str]
    active: bool


class CustomerRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_name: str
    country_code: str
    contact_name: str | None
    email: str | None
    preferred_language: str
    created_at: datetime
    updated_at: datetime


class CustomerMemoryRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    customer_id: str
    category: MemoryCategory
    content: str
    confidence: float = Field(ge=0, le=1)
    source_inquiry_id: str | None
    is_active: bool
    created_at: datetime
    invalidated_at: datetime | None


class OpportunitySummaryRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    inquiry_id: str
    customer_id: str
    title: str
    stage: OpportunityStage
    priority: OpportunityPriority
    score: int = Field(ge=0, le=100)
    market: str
    channel: str | None
    estimated_bottles: int | None
    target_date: date | None
    summary: str
    created_at: datetime
    updated_at: datetime
