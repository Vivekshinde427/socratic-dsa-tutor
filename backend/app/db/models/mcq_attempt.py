import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class MCQAttempt(Base):
    """Records a student's MCQ answer attempt."""
    __tablename__ = "mcq_attempts"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String, ForeignKey("sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    step_id: Mapped[str] = mapped_column(String, default="", nullable=False)
    step_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    selected_option_id: Mapped[str] = mapped_column(String, nullable=False)
    correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    misconception_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    hint_level_at_attempt: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    session: Mapped["Session"] = relationship("Session", back_populates="mcq_attempts")
