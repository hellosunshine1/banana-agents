from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    topic: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    genre: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    num_chapters: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    word_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    model_routing: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    architecture: Mapped[str] = mapped_column(Text, nullable=False, default="")
    character_state: Mapped[str] = mapped_column(Text, nullable=False, default="")
    global_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
