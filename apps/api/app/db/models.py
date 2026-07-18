"""SQLAlchemy models for AdegaFlow AI persistence."""

from datetime import UTC, date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(UTC)


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint(
            "price_cents >= 0",
            name="ck_products_price_non_negative",
        ),
        CheckConstraint(
            "units_per_case > 0",
            name="ck_products_units_per_case_positive",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    sku: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        index=True,
    )
    variety: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        index=True,
    )
    vintage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    units_per_case: Mapped[int] = mapped_column(Integer, nullable=False)
    recommended_markets: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    recommended_channels: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    tasting_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    certifications: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )


class Inventory(Base):
    __tablename__ = "inventory"
    __table_args__ = (
        CheckConstraint(
            "available_bottles >= 0",
            name="ck_inventory_available_non_negative",
        ),
        CheckConstraint(
            "reserved_bottles >= 0",
            name="ck_inventory_reserved_non_negative",
        ),
    )

    product_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
    )
    available_bottles: Mapped[int] = mapped_column(Integer, nullable=False)
    reserved_bottles: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint(
            "company_name",
            "country_code",
            name="uq_customer_company_country",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    company_name: Mapped[str] = mapped_column(
        String(160),
        nullable=False,
        index=True,
    )
    country_code: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        index=True,
    )
    contact_name: Mapped[str | None] = mapped_column(
        String(160),
        nullable=True,
    )
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    preferred_language: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        default="en",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


class Inquiry(Base):
    __tablename__ = "inquiries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    customer_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    raw_message: Mapped[str] = mapped_column(Text, nullable=False)
    detected_language: Mapped[str | None] = mapped_column(
        String(2),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="new",
    )
    extracted_data: Mapped[dict[str, object]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    missing_fields: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


class CustomerMemory(Base):
    __tablename__ = "customer_memories"
    __table_args__ = (
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_customer_memories_confidence_range",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    customer_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    source_inquiry_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("inquiries.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    invalidated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class Opportunity(Base):
    __tablename__ = "opportunities"
    __table_args__ = (
        CheckConstraint(
            "score >= 0 AND score <= 100",
            name="ck_opportunities_score_range",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    inquiry_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("inquiries.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    customer_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    market: Mapped[str] = mapped_column(String(80), nullable=False)
    channel: Mapped[str | None] = mapped_column(String(80), nullable=True)
    estimated_bottles: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


class AgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        UniqueConstraint(
            "correlation_id",
            name="uq_agent_runs_correlation_id",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    inquiry_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("inquiries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    correlation_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="queued",
        index=True,
    )
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_versions: Mapped[dict[str, object]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    result_payload: Mapped[dict[str, object]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    current_step: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="queued",
    )
    error_code: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    error_message_safe: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )


class ToolExecution(Base):
    __tablename__ = "tool_executions"
    __table_args__ = (
        UniqueConstraint(
            "agent_run_id",
            "sequence",
            name="uq_tool_executions_run_sequence",
        ),
        CheckConstraint(
            "sequence > 0",
            name="ck_tool_executions_sequence_positive",
        ),
        CheckConstraint(
            "duration_ms >= 0",
            name="ck_tool_executions_duration_non_negative",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    agent_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    tool_name: Mapped[str] = mapped_column(String(80), nullable=False)
    input_payload: Mapped[dict[str, object]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    output_payload: Mapped[dict[str, object]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="started",
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    duration_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    error_code: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )


class AgentRunEvent(Base):
    __tablename__ = "agent_run_events"
    __table_args__ = (
        UniqueConstraint(
            "agent_run_id",
            "sequence",
            name="uq_agent_run_events_run_sequence",
        ),
        CheckConstraint(
            "sequence > 0",
            name="ck_agent_run_events_sequence_positive",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    agent_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    step: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


class Quote(Base):
    __tablename__ = "quotes"
    __table_args__ = (
        UniqueConstraint(
            "agent_run_id",
            name="uq_quotes_agent_run_id",
        ),
        CheckConstraint(
            "currency = 'EUR'",
            name="ck_quotes_currency_eur",
        ),
        CheckConstraint(
            "subtotal_cents >= 0",
            name="ck_quotes_subtotal_non_negative",
        ),
        CheckConstraint(
            "status IN ('draft', 'reviewed')",
            name="ck_quotes_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    agent_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="EUR",
    )
    subtotal_cents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="draft",
    )
    assumptions: Mapped[dict[str, object]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


class QuoteItem(Base):
    __tablename__ = "quote_items"
    __table_args__ = (
        UniqueConstraint(
            "quote_id",
            "product_id",
            name="uq_quote_items_quote_product",
        ),
        CheckConstraint(
            "quantity_bottles > 0",
            name="ck_quote_items_quantity_positive",
        ),
        CheckConstraint(
            "unit_price_cents >= 0",
            name="ck_quote_items_unit_price_non_negative",
        ),
        CheckConstraint(
            "line_total_cents >= 0",
            name="ck_quote_items_line_total_non_negative",
        ),
        CheckConstraint(
            "line_total_cents = quantity_bottles * unit_price_cents",
            name="ck_quote_items_line_total_exact",
        ),
        CheckConstraint(
            "cases > 0",
            name="ck_quote_items_cases_positive",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    quote_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("quotes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity_bottles: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    unit_price_cents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    line_total_cents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    cases: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )


class GeneratedArtifact(Base):
    __tablename__ = "generated_artifacts"
    __table_args__ = (
        UniqueConstraint(
            "agent_run_id",
            "artifact_type",
            name="uq_generated_artifacts_run_type",
        ),
        CheckConstraint(
            "artifact_type IN ('proposal', 'email_draft')",
            name="ck_generated_artifacts_type",
        ),
        CheckConstraint(
            "review_status IN ('needs_review', 'approved')",
            name="ck_generated_artifacts_review_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    agent_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quote_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("quotes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    artifact_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    language: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
    )
    schema_version: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    content: Mapped[dict[str, object]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    review_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="needs_review",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
