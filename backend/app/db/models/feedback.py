import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class Feedback(Base):
    """Student feedback on a tutoring session."""
    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String, ForeignKey("sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
