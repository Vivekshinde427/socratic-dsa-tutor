import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class Session(Base):
    """A tutoring session linking a user to a problem."""
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    problem_id: Mapped[str] = mapped_column(
        String, ForeignKey("problems.id", ondelete="CASCADE"), index=True, nullable=False
    )
    plan_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("problem_plans.id", ondelete="SET NULL"), nullable=True
    )
    # Current position in the Socratic journey
    current_step_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_hint_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(
        String, default="active", nullable=False
    )  # active, completed, abandoned
    # Stage completion evidence as JSON: {"understand": "completed", "brute_force": "active", ...}
    stage_progress: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    # Rolling summary for context management
    rolling_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="session", cascade="all, delete-orphan",
        order_by="Message.created_at"
    )
    mcq_attempts: Mapped[List["MCQAttempt"]] = relationship(
        "MCQAttempt", back_populates="session", cascade="all, delete-orphan"
    )
    code_runs: Mapped[List["CodeRun"]] = relationship(
        "CodeRun", back_populates="session", cascade="all, delete-orphan"
    )
