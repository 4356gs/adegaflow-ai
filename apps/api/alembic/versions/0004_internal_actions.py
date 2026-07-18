"""Add deterministic internal-action persistence.

Revision ID: 0004_internal_actions
Revises: 0003_quote_artifacts
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_internal_actions"
down_revision: str | None = "0003_quote_artifacts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "follow_up_tasks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("opportunity_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'completed')",
            name="ck_follow_up_tasks_status",
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_follow_up_tasks_opportunity_id",
        "follow_up_tasks",
        ["opportunity_id"],
    )

    op.create_table(
        "internal_action_receipts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("agent_run_id", sa.String(length=36), nullable=False),
        sa.Column("action_name", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("result_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "action_name IN ('create_crm_opportunity', "
            "'create_followup_task', 'save_customer_memory')",
            name="ck_internal_action_receipts_action_name",
        ),
        sa.CheckConstraint(
            "length(request_fingerprint) = 64",
            name="ck_internal_action_receipts_fingerprint_length",
        ),
        sa.ForeignKeyConstraint(
            ["agent_run_id"], ["agent_runs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "agent_run_id",
            "action_name",
            name="uq_internal_action_receipts_run_action",
        ),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_internal_action_receipts_idempotency_key",
        ),
    )
    op.create_index(
        "ix_internal_action_receipts_agent_run_id",
        "internal_action_receipts",
        ["agent_run_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_internal_action_receipts_agent_run_id",
        table_name="internal_action_receipts",
    )
    op.drop_table("internal_action_receipts")
    op.drop_index(
        "ix_follow_up_tasks_opportunity_id", table_name="follow_up_tasks"
    )
    op.drop_table("follow_up_tasks")
