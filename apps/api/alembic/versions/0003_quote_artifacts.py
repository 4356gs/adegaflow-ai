"""Add deterministic quotes and generated artifacts.

Revision ID: 0003_quote_artifacts
Revises: 0002_agent_run_traceability
Create Date: 2026-07-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_quote_artifacts"
down_revision: str | None = "0002_agent_run_traceability"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "quotes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("agent_run_id", sa.String(length=36), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("subtotal_cents", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("assumptions", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "currency = 'EUR'",
            name="ck_quotes_currency_eur",
        ),
        sa.CheckConstraint(
            "subtotal_cents >= 0",
            name="ck_quotes_subtotal_non_negative",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'reviewed')",
            name="ck_quotes_status",
        ),
        sa.ForeignKeyConstraint(
            ["agent_run_id"],
            ["agent_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "agent_run_id",
            name="uq_quotes_agent_run_id",
        ),
    )

    op.create_table(
        "quote_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("quote_id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.String(length=36), nullable=False),
        sa.Column("quantity_bottles", sa.Integer(), nullable=False),
        sa.Column("unit_price_cents", sa.Integer(), nullable=False),
        sa.Column("line_total_cents", sa.Integer(), nullable=False),
        sa.Column("cases", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "quantity_bottles > 0",
            name="ck_quote_items_quantity_positive",
        ),
        sa.CheckConstraint(
            "unit_price_cents >= 0",
            name="ck_quote_items_unit_price_non_negative",
        ),
        sa.CheckConstraint(
            "line_total_cents >= 0",
            name="ck_quote_items_line_total_non_negative",
        ),
        sa.CheckConstraint(
            "line_total_cents = quantity_bottles * unit_price_cents",
            name="ck_quote_items_line_total_exact",
        ),
        sa.CheckConstraint(
            "cases > 0",
            name="ck_quote_items_cases_positive",
        ),
        sa.ForeignKeyConstraint(
            ["quote_id"],
            ["quotes.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "quote_id",
            "product_id",
            name="uq_quote_items_quote_product",
        ),
    )

    op.create_index(
        "ix_quote_items_quote_id",
        "quote_items",
        ["quote_id"],
    )
    op.create_index(
        "ix_quote_items_product_id",
        "quote_items",
        ["product_id"],
    )

    op.create_table(
        "generated_artifacts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("agent_run_id", sa.String(length=36), nullable=False),
        sa.Column("quote_id", sa.String(length=36), nullable=False),
        sa.Column("artifact_type", sa.String(length=32), nullable=False),
        sa.Column("language", sa.String(length=2), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("review_status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "artifact_type IN ('proposal', 'email_draft')",
            name="ck_generated_artifacts_type",
        ),
        sa.CheckConstraint(
            "review_status IN ('needs_review', 'approved')",
            name="ck_generated_artifacts_review_status",
        ),
        sa.ForeignKeyConstraint(
            ["agent_run_id"],
            ["agent_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["quote_id"],
            ["quotes.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "agent_run_id",
            "artifact_type",
            name="uq_generated_artifacts_run_type",
        ),
    )

    op.create_index(
        "ix_generated_artifacts_agent_run_id",
        "generated_artifacts",
        ["agent_run_id"],
    )
    op.create_index(
        "ix_generated_artifacts_quote_id",
        "generated_artifacts",
        ["quote_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_generated_artifacts_quote_id",
        table_name="generated_artifacts",
    )
    op.drop_index(
        "ix_generated_artifacts_agent_run_id",
        table_name="generated_artifacts",
    )
    op.drop_table("generated_artifacts")

    op.drop_index(
        "ix_quote_items_product_id",
        table_name="quote_items",
    )
    op.drop_index(
        "ix_quote_items_quote_id",
        table_name="quote_items",
    )
    op.drop_table("quote_items")
    op.drop_table("quotes")