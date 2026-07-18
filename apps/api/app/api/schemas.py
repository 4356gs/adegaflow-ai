"""Strict public HTTP contracts for Sprint 2 Block 8."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import AgentRunStatus, AgentRunStep, InquiryStatus


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class ErrorBody(StrictSchema):
    code: str
    message: str
    details: dict[str, object] = Field(default_factory=dict)
    correlation_id: UUID


class ErrorEnvelope(StrictSchema):
    error: ErrorBody


class InquiryCreate(StrictSchema):
    source: Literal["manual", "demo"]
    raw_message: str = Field(min_length=1, max_length=10_000)
    customer_id: UUID | None = None

    @field_validator("raw_message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("raw_message must contain non-whitespace characters")
        return normalized


class InquirySummary(StrictSchema):
    id: UUID
    customer_id: UUID | None
    source: str
    status: InquiryStatus
    detected_language: str | None
    received_at: datetime


class InquiryList(StrictSchema):
    items: list[InquirySummary]
    limit: int
    offset: int


class RunReference(StrictSchema):
    id: UUID
    status: AgentRunStatus
    current_step: AgentRunStep
    started_at: datetime
    completed_at: datetime | None


class InquiryDetail(InquirySummary):
    raw_message: str
    extracted_data: dict[str, object]
    missing_fields: list[str]
    agent_runs: list[RunReference]


class RunAccepted(StrictSchema):
    agent_run_id: UUID
    inquiry_id: UUID
    status: AgentRunStatus
    current_step: AgentRunStep
    correlation_id: UUID
    retry_of_run_id: UUID | None
    poll_url: str


class PublicRunError(StrictSchema):
    code: str
    message: str


class RunReferences(StrictSchema):
    quote_id: UUID | None = None
    proposal_id: UUID | None = None
    email_draft_id: UUID | None = None
    opportunity_id: UUID | None = None
    followup_task_id: UUID | None = None


class AgentRunDetail(StrictSchema):
    id: UUID
    inquiry_id: UUID
    retry_of_run_id: UUID | None
    correlation_id: UUID
    status: AgentRunStatus
    current_step: AgentRunStep
    started_at: datetime
    completed_at: datetime | None
    model: str
    prompt_versions: dict[str, object]
    error: PublicRunError | None
    retryable: bool
    references: RunReferences
    last_event_sequence: int = Field(ge=0)
    events_url: str
    result_url: str


class AgentRunSummary(StrictSchema):
    id: UUID
    inquiry_id: UUID
    retry_of_run_id: UUID | None
    status: AgentRunStatus
    current_step: AgentRunStep
    company_name: str | None
    market: str | None
    received_at: datetime
    started_at: datetime
    completed_at: datetime | None
    error_code: str | None
    retryable: bool


class AgentRunList(StrictSchema):
    items: list[AgentRunSummary]
    limit: int
    offset: int


class PublicEvent(StrictSchema):
    sequence: int = Field(gt=0)
    event_type: str
    step: AgentRunStep
    payload: dict[str, object]
    created_at: datetime


class EventList(StrictSchema):
    agent_run_id: UUID
    events: list[PublicEvent]
    last_sequence: int = Field(ge=0)
    terminal: bool


class QuoteItemPublic(StrictSchema):
    product_id: UUID
    sku: str
    name: str
    quantity_bottles: int
    unit_price_cents: int
    line_total_cents: int
    cases: int


class QuotePublic(StrictSchema):
    id: UUID
    currency: Literal["EUR"]
    subtotal_cents: int
    status: str
    assumptions: dict[str, object]
    items: list[QuoteItemPublic]


class ArtifactPublic(StrictSchema):
    id: UUID
    artifact_type: str
    language: str
    schema_version: str
    content: dict[str, object]
    review_status: str
    created_at: datetime


class CustomerPublic(StrictSchema):
    id: UUID
    company_name: str
    country_code: str
    preferred_language: str


class OpportunityPublic(StrictSchema):
    id: UUID
    inquiry_id: UUID
    customer_id: UUID
    title: str
    stage: str
    priority: str
    score: int
    market: str
    channel: str | None
    estimated_bottles: int | None
    target_date: date | None
    summary: str
    created_at: datetime
    updated_at: datetime


class FollowUpPublic(StrictSchema):
    id: UUID
    opportunity_id: UUID
    title: str
    due_at: datetime
    status: str
    created_at: datetime


class MemoryPublic(StrictSchema):
    id: UUID
    customer_id: UUID
    category: str
    content: str
    confidence: float
    source_inquiry_id: UUID | None
    created_at: datetime


class MemoryList(StrictSchema):
    customer_id: UUID
    items: list[MemoryPublic]
    limit: int
    offset: int


class RunResult(StrictSchema):
    agent_run_id: UUID
    status: AgentRunStatus
    inquiry: InquiryDetail
    analysis: dict[str, object] | None
    recommendation: dict[str, object] | None
    quote: QuotePublic | None
    artifacts: list[ArtifactPublic]
    customer: CustomerPublic | None
    opportunity: OpportunityPublic | None
    followup: FollowUpPublic | None
    memory_summary: list[MemoryPublic]
    warnings: list[str]


class OpportunityDetail(OpportunityPublic):
    customer: CustomerPublic
    inquiry_id: UUID
    quote: QuotePublic | None
    artifacts: list[ArtifactPublic]
    followup: FollowUpPublic | None
