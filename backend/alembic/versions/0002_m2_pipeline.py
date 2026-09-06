"""m2 pipeline tables

Revision ID: 0002_m2_pipeline
Revises: 0001_m1_init
Create Date: 2026-09-06

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0002_m2_pipeline"
down_revision: Union[str, None] = "0001_m1_init"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chapter_blueprints",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("chapter_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("raw_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "chapter_number", name="uq_blueprint_project_chapter"),
    )
    op.create_index("ix_chapter_blueprints_project_id", "chapter_blueprints", ["project_id"])

    op.create_table(
        "chapters",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("chapter_number", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="empty"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "chapter_number", name="uq_chapter_project_number"),
    )
    op.create_index("ix_chapters_project_id", "chapters", ["project_id"])

    op.create_table(
        "chapter_chunks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("chapter_number", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chapter_chunks_project_id", "chapter_chunks", ["project_id"])
    op.create_index(
        "ix_chapter_chunks_project_chapter",
        "chapter_chunks",
        ["project_id", "chapter_number"],
    )


def downgrade() -> None:
    op.drop_index("ix_chapter_chunks_project_chapter", table_name="chapter_chunks")
    op.drop_index("ix_chapter_chunks_project_id", table_name="chapter_chunks")
    op.drop_table("chapter_chunks")
    op.drop_index("ix_chapters_project_id", table_name="chapters")
    op.drop_table("chapters")
    op.drop_index("ix_chapter_blueprints_project_id", table_name="chapter_blueprints")
    op.drop_table("chapter_blueprints")
