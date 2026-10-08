import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class Message(Base):
    """A single message in a tutoring session conversation."""
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String, ForeignKey("sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(
        String, nullable=False
    )  # "student", "tutor", "system"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(
        String, default="text", nullable=False
    )  # "text", "mcq", "mcq_answer", "hint_request", "code_run", "formative_feedback", "deflection"
    # Metadata for MCQ steps, evaluations, etc.
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    step_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    session: Mapped["Session"] = relationship("Session", back_populates="messages")
