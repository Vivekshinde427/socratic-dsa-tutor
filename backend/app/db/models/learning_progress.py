import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class LearningProgress(Base):
    """Per-user per-topic mastery tracking."""
    __tablename__ = "learning_progress"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    topic: Mapped[str] = mapped_column(String, index=True, nullable=False)
    mastery: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # [0, 1]
    problems_attempted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    problems_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_hints_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
