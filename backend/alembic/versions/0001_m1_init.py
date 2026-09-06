"""m1 init tables

Revision ID: 0001_m1_init
Revises:
Create Date: 2026-09-06

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_m1_init"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("llm_configs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("embedding_configs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("choose_configs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("topic", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("genre", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("num_chapters", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("word_number", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("model_routing", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("architecture", sa.Text(), nullable=False, server_default=""),
        sa.Column("character_state", sa.Text(), nullable=False, server_default=""),
        sa.Column("global_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"], unique=False)

    op.create_table(
        "generation_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("result_ref", sa.String(length=255), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_generation_jobs_project_id", "generation_jobs", ["project_id"], unique=False)
    op.create_index("ix_generation_jobs_user_id", "generation_jobs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_generation_jobs_user_id", table_name="generation_jobs")
    op.drop_index("ix_generation_jobs_project_id", table_name="generation_jobs")
    op.drop_table("generation_jobs")
    op.drop_index("ix_projects_owner_id", table_name="projects")
    op.drop_table("projects")
    op.drop_table("app_settings")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
