import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class CodeRun(Base):
    """Records a student's code execution attempt."""
    __tablename__ = "code_runs"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String, ForeignKey("sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    language: Mapped[str] = mapped_column(String, default="python", nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    run_type: Mapped[str] = mapped_column(
        String, default="run", nullable=False
    )  # "run" or "submit"
    status: Mapped[str] = mapped_column(String, nullable=False)  # SUCCESS, RUNTIME_ERROR, etc.
    stdout: Mapped[str] = mapped_column(Text, default="", nullable=False)
    stderr: Mapped[str] = mapped_column(Text, default="", nullable=False)
    execution_time_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    tests_passed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tests_total: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    test_results: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    session: Mapped["Session"] = relationship("Session", back_populates="code_runs")
