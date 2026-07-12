"""Load deterministic demo data into the configured database."""

import argparse
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import (
    Customer,
    CustomerMemory,
    Inquiry,
    Inventory,
    Opportunity,
    Product,
)
from app.db.session import session_scope
from app.domain.enums import (
    InquirySource,
    InquiryStatus,
    MemoryCategory,
    OpportunityPriority,
    OpportunityStage,
)


class OrganizationSeed(BaseModel):
    name: str
    region: str
    currency: str
    default_language: str
    demo_only: bool


class InventorySeed(BaseModel):
    available_bottles: int = Field(ge=0)
    reserved_bottles: int = Field(ge=0)
    updated_at: datetime


class ProductSeed(BaseModel):
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
    inventory: InventorySeed


class CustomerSeed(BaseModel):
    id: str
    company_name: str
    country_code: str = Field(min_length=2, max_length=2)
    contact_name: str | None
    email: str | None
    preferred_language: str = Field(min_length=2, max_length=2)
    created_at: datetime
    updated_at: datetime


class InquirySeed(BaseModel):
    id: str
    customer_id: str | None
    source: InquirySource
    raw_message: str
    detected_language: str | None
    status: InquiryStatus
    extracted_data: dict[str, Any]
    missing_fields: list[str]
    received_at: datetime


class CustomerMemorySeed(BaseModel):
    id: str
    customer_id: str
    category: MemoryCategory
    content: str
    confidence: float = Field(ge=0, le=1)
    source_inquiry_id: str | None
    is_active: bool
    created_at: datetime
    invalidated_at: datetime | None


class OpportunitySeed(BaseModel):
    id: str
    inquiry_id: str
    customer_id: str
    title: str
    stage: OpportunityStage
    priority: OpportunityPriority
    score: int = Field(ge=0, le=100)
    market: str
    channel: str | None
    estimated_bottles: int | None = Field(default=None, ge=0)
    target_date: date | None
    summary: str
    created_at: datetime
    updated_at: datetime


class DemoSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seed_version: str
    organization: OrganizationSeed
    products: list[ProductSeed]
    customers: list[CustomerSeed]
    inquiries: list[InquirySeed]
    customer_memories: list[CustomerMemorySeed]
    opportunities: list[OpportunitySeed]


class SeedSummary(BaseModel):
    seed_version: str
    products: int
    inventory: int
    customers: int
    inquiries: int
    customer_memories: int
    opportunities: int


def resolve_seed_path(seed_path: str | Path) -> Path:
    """Resolve a seed path from the current directory or repository root."""

    path = Path(seed_path).expanduser()
    if path.is_absolute() or path.exists():
        return path.resolve()

    repository_root = Path(__file__).resolve().parents[4]
    return (repository_root / path).resolve()


def load_seed_file(seed_path: str | Path) -> DemoSeed:
    """Read and validate a demo seed JSON file."""

    path = resolve_seed_path(seed_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    return DemoSeed.model_validate(payload)


def reset_demo_data(session: Session) -> None:
    """Remove records owned by the reproducible demo dataset."""

    for model in (
        Opportunity,
        CustomerMemory,
        Inquiry,
        Inventory,
        Product,
        Customer,
    ):
        session.execute(delete(model))
    session.flush()
    session.expunge_all()


def seed_demo_data(session: Session, seed: DemoSeed, *, reset: bool = False) -> SeedSummary:
    """Upsert the validated demo dataset and return stable table counts."""

    if reset:
        reset_demo_data(session)

    for customer_seed in seed.customers:
        session.merge(
            Customer(
                id=customer_seed.id,
                company_name=customer_seed.company_name,
                country_code=customer_seed.country_code.upper(),
                contact_name=customer_seed.contact_name,
                email=customer_seed.email,
                preferred_language=customer_seed.preferred_language.lower(),
                created_at=customer_seed.created_at,
                updated_at=customer_seed.updated_at,
            )
        )

    for product_seed in seed.products:
        session.merge(
            Product(
                id=product_seed.id,
                sku=product_seed.sku,
                name=product_seed.name,
                category=product_seed.category,
                variety=product_seed.variety,
                vintage=product_seed.vintage,
                description=product_seed.description,
                price_cents=product_seed.price_cents,
                units_per_case=product_seed.units_per_case,
                recommended_markets=[
                    market.upper() for market in product_seed.recommended_markets
                ],
                recommended_channels=product_seed.recommended_channels,
                tasting_notes=product_seed.tasting_notes,
                certifications=product_seed.certifications,
                active=product_seed.active,
            )
        )
        session.merge(
            Inventory(
                product_id=product_seed.id,
                available_bottles=product_seed.inventory.available_bottles,
                reserved_bottles=product_seed.inventory.reserved_bottles,
                updated_at=product_seed.inventory.updated_at,
            )
        )

    for inquiry_seed in seed.inquiries:
        session.merge(
            Inquiry(
                id=inquiry_seed.id,
                customer_id=inquiry_seed.customer_id,
                source=inquiry_seed.source.value,
                raw_message=inquiry_seed.raw_message,
                detected_language=inquiry_seed.detected_language,
                status=inquiry_seed.status.value,
                extracted_data=inquiry_seed.extracted_data,
                missing_fields=inquiry_seed.missing_fields,
                received_at=inquiry_seed.received_at,
            )
        )

    for memory_seed in seed.customer_memories:
        session.merge(
            CustomerMemory(
                id=memory_seed.id,
                customer_id=memory_seed.customer_id,
                category=memory_seed.category.value,
                content=memory_seed.content,
                confidence=memory_seed.confidence,
                source_inquiry_id=memory_seed.source_inquiry_id,
                is_active=memory_seed.is_active,
                created_at=memory_seed.created_at,
                invalidated_at=memory_seed.invalidated_at,
            )
        )

    for opportunity_seed in seed.opportunities:
        session.merge(
            Opportunity(
                id=opportunity_seed.id,
                inquiry_id=opportunity_seed.inquiry_id,
                customer_id=opportunity_seed.customer_id,
                title=opportunity_seed.title,
                stage=opportunity_seed.stage.value,
                priority=opportunity_seed.priority.value,
                score=opportunity_seed.score,
                market=opportunity_seed.market,
                channel=opportunity_seed.channel,
                estimated_bottles=opportunity_seed.estimated_bottles,
                target_date=opportunity_seed.target_date,
                summary=opportunity_seed.summary,
                created_at=opportunity_seed.created_at,
                updated_at=opportunity_seed.updated_at,
            )
        )

    session.flush()
    return SeedSummary(
        seed_version=seed.seed_version,
        products=session.scalar(select(func.count()).select_from(Product)) or 0,
        inventory=session.scalar(select(func.count()).select_from(Inventory)) or 0,
        customers=session.scalar(select(func.count()).select_from(Customer)) or 0,
        inquiries=session.scalar(select(func.count()).select_from(Inquiry)) or 0,
        customer_memories=session.scalar(select(func.count()).select_from(CustomerMemory)) or 0,
        opportunities=session.scalar(select(func.count()).select_from(Opportunity)) or 0,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-file", default=None, help="Path to a demo seed JSON file.")
    parser.add_argument("--reset", action="store_true", help="Delete demo tables before loading.")
    args = parser.parse_args()

    settings = get_settings()
    seed_path = args.seed_file or settings.demo_seed_path
    seed = load_seed_file(seed_path)
    with session_scope() as session:
        summary = seed_demo_data(session, seed, reset=args.reset)
    print(summary.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
