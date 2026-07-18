"""Add HTTP idempotency and retry lineage for asynchronous runs.

Revision ID: 0005_http_async_runs
Revises: 0004_internal_actions
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_http_async_runs"
down_revision: str | None = "0004_internal_actions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("inquiries") as batch_op:
        batch_op.add_column(sa.Column("submission_key", sa.String(160), nullable=True))
    op.create_index(
        "uq_inquiries_submission_key",
        "inquiries",
        ["submission_key"],
        unique=True,
        sqlite_where=sa.text("submission_key IS NOT NULL"),
    )

    with op.batch_alter_table("agent_runs") as batch_op:
        batch_op.add_column(sa.Column("request_key", sa.String(160), nullable=True))
        batch_op.add_column(sa.Column("retry_of_run_id", sa.String(36), nullable=True))
        batch_op.create_foreign_key(
            "fk_agent_runs_retry_of_run_id",
            "agent_runs",
            ["retry_of_run_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index(
        "uq_agent_runs_request_key",
        "agent_runs",
        ["request_key"],
        unique=True,
        sqlite_where=sa.text("request_key IS NOT NULL"),
    )
    op.create_index(
        "ix_agent_runs_retry_of_run_id",
        "agent_runs",
        ["retry_of_run_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_agent_runs_retry_of_run_id", table_name="agent_runs")
    op.drop_index("uq_agent_runs_request_key", table_name="agent_runs")
    with op.batch_alter_table("agent_runs") as batch_op:
        batch_op.drop_constraint("fk_agent_runs_retry_of_run_id", type_="foreignkey")
        batch_op.drop_column("retry_of_run_id")
        batch_op.drop_column("request_key")

    op.drop_index("uq_inquiries_submission_key", table_name="inquiries")
    with op.batch_alter_table("inquiries") as batch_op:
        batch_op.drop_column("submission_key")
