"""m3 agent and consistency review

Revision ID: 0003_m3_agent_review
Revises: 0002_m2_pipeline
Create Date: 2026-09-06

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_m3_agent_review"
down_revision: Union[str, None] = "0002_m2_pipeline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "consistency_reviews",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("chapter_number", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=True),
        sa.Column("conflicts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["generation_jobs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_consistency_reviews_project_id", "consistency_reviews", ["project_id"])
    op.create_index(
        "ix_consistency_reviews_project_chapter",
        "consistency_reviews",
        ["project_id", "chapter_number"],
    )

    op.create_table(
        "agent_audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("user_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("intent", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("tool_name", sa.String(length=64), nullable=True),
        sa.Column("tool_args", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ok"),
        sa.Column("result_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_audit_logs_project_id", "agent_audit_logs", ["project_id"])
    op.create_index("ix_agent_audit_logs_user_id", "agent_audit_logs", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_audit_logs_user_id", table_name="agent_audit_logs")
    op.drop_index("ix_agent_audit_logs_project_id", table_name="agent_audit_logs")
    op.drop_table("agent_audit_logs")
    op.drop_index("ix_consistency_reviews_project_chapter", table_name="consistency_reviews")
    op.drop_index("ix_consistency_reviews_project_id", table_name="consistency_reviews")
    op.drop_table("consistency_reviews")
