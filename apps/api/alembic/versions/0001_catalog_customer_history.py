"""Add catalog, stock, customers, memories and history.

Revision ID: 0001_catalog_customer_history
Revises:
Create Date: 2026-07-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_catalog_customer_history"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_name", sa.String(length=160), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("contact_name", sa.String(length=160), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("preferred_language", sa.String(length=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_name",
            "country_code",
            name="uq_customer_company_country",
        ),
    )
    op.create_index("ix_customers_company_name", "customers", ["company_name"])
    op.create_index("ix_customers_country_code", "customers", ["country_code"])

    op.create_table(
        "products",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("variety", sa.String(length=80), nullable=False),
        sa.Column("vintage", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column("units_per_case", sa.Integer(), nullable=False),
        sa.Column("recommended_markets", sa.JSON(), nullable=False),
        sa.Column("recommended_channels", sa.JSON(), nullable=False),
        sa.Column("tasting_notes", sa.Text(), nullable=True),
        sa.Column("certifications", sa.JSON(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.CheckConstraint("price_cents >= 0", name="ck_products_price_non_negative"),
        sa.CheckConstraint(
            "units_per_case > 0",
            name="ck_products_units_per_case_positive",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sku"),
    )
    op.create_index("ix_products_active", "products", ["active"])
    op.create_index("ix_products_category", "products", ["category"])
    op.create_index("ix_products_sku", "products", ["sku"])
    op.create_index("ix_products_variety", "products", ["variety"])

    op.create_table(
        "inventory",
        sa.Column("product_id", sa.String(length=36), nullable=False),
        sa.Column("available_bottles", sa.Integer(), nullable=False),
        sa.Column("reserved_bottles", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "available_bottles >= 0",
            name="ck_inventory_available_non_negative",
        ),
        sa.CheckConstraint(
            "reserved_bottles >= 0",
            name="ck_inventory_reserved_non_negative",
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("product_id"),
    )

    op.create_table(
        "inquiries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("customer_id", sa.String(length=36), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("raw_message", sa.Text(), nullable=False),
        sa.Column("detected_language", sa.String(length=2), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("extracted_data", sa.JSON(), nullable=False),
        sa.Column("missing_fields", sa.JSON(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inquiries_customer_id", "inquiries", ["customer_id"])

    op.create_table(
        "customer_memories",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("customer_id", sa.String(length=36), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("source_inquiry_id", sa.String(length=36), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_customer_memories_confidence_range",
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["source_inquiry_id"],
            ["inquiries.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customer_memories_category", "customer_memories", ["category"])
    op.create_index("ix_customer_memories_customer_id", "customer_memories", ["customer_id"])
    op.create_index("ix_customer_memories_is_active", "customer_memories", ["is_active"])

    op.create_table(
        "opportunities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("inquiry_id", sa.String(length=36), nullable=False),
        sa.Column("customer_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("market", sa.String(length=80), nullable=False),
        sa.Column("channel", sa.String(length=80), nullable=True),
        sa.Column("estimated_bottles", sa.Integer(), nullable=True),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "score >= 0 AND score <= 100",
            name="ck_opportunities_score_range",
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["inquiry_id"], ["inquiries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("inquiry_id"),
    )
    op.create_index("ix_opportunities_customer_id", "opportunities", ["customer_id"])


def downgrade() -> None:
    op.drop_index("ix_opportunities_customer_id", table_name="opportunities")
    op.drop_table("opportunities")
    op.drop_index("ix_customer_memories_is_active", table_name="customer_memories")
    op.drop_index("ix_customer_memories_customer_id", table_name="customer_memories")
    op.drop_index("ix_customer_memories_category", table_name="customer_memories")
    op.drop_table("customer_memories")
    op.drop_index("ix_inquiries_customer_id", table_name="inquiries")
    op.drop_table("inquiries")
    op.drop_table("inventory")
    op.drop_index("ix_products_variety", table_name="products")
    op.drop_index("ix_products_sku", table_name="products")
    op.drop_index("ix_products_category", table_name="products")
    op.drop_index("ix_products_active", table_name="products")
    op.drop_table("products")
    op.drop_index("ix_customers_country_code", table_name="customers")
    op.drop_index("ix_customers_company_name", table_name="customers")
    op.drop_table("customers")
