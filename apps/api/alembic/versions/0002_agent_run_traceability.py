"""Add agent-run traceability tables.

Revision ID: 0002_agent_run_traceability
Revises: 0001_catalog_customer_history
Create Date: 2026-07-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_agent_run_traceability"
down_revision: str | None = "0001_catalog_customer_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("inquiry_id", sa.String(length=36), nullable=False),
        sa.Column("correlation_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("prompt_versions", sa.JSON(), nullable=False),
        sa.Column("result_payload", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_step", sa.String(length=64), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message_safe", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(
            ["inquiry_id"],
            ["inquiries.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "correlation_id",
            name="uq_agent_runs_correlation_id",
        ),
    )
    op.create_index(
        "ix_agent_runs_inquiry_id",
        "agent_runs",
        ["inquiry_id"],
    )
    op.create_index(
        "ix_agent_runs_status",
        "agent_runs",
        ["status"],
    )

    op.create_table(
        "tool_executions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("agent_run_id", sa.String(length=36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("tool_name", sa.String(length=80), nullable=False),
        sa.Column("input_payload", sa.JSON(), nullable=False),
        sa.Column("output_payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "sequence > 0",
            name="ck_tool_executions_sequence_positive",
        ),
        sa.CheckConstraint(
            "duration_ms >= 0",
            name="ck_tool_executions_duration_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["agent_run_id"],
            ["agent_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "agent_run_id",
            "sequence",
            name="uq_tool_executions_run_sequence",
        ),
    )
    op.create_index(
        "ix_tool_executions_agent_run_id",
        "tool_executions",
        ["agent_run_id"],
    )

    op.create_table(
        "agent_run_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("agent_run_id", sa.String(length=36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("step", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "sequence > 0",
            name="ck_agent_run_events_sequence_positive",
        ),
        sa.ForeignKeyConstraint(
            ["agent_run_id"],
            ["agent_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "agent_run_id",
            "sequence",
            name="uq_agent_run_events_run_sequence",
        ),
    )
    op.create_index(
        "ix_agent_run_events_agent_run_id",
        "agent_run_events",
        ["agent_run_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_agent_run_events_agent_run_id",
        table_name="agent_run_events",
    )
    op.drop_table("agent_run_events")

    op.drop_index(
        "ix_tool_executions_agent_run_id",
        table_name="tool_executions",
    )
    op.drop_table("tool_executions")

    op.drop_index("ix_agent_runs_status", table_name="agent_runs")
    op.drop_index("ix_agent_runs_inquiry_id", table_name="agent_runs")
    op.drop_table("agent_runs")
