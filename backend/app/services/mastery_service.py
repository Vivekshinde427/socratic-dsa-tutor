"""
Mastery tracking service (SPEC §15).
Per user and topic, keep mastery in [0, 1] using a simple explainable update model.
"""
from typing import Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import logger
from backend.app.db.models.learning_progress import LearningProgress


# Mastery update constants
CORRECT_FIRST_TRY_DELTA = 0.15
CORRECT_WITH_HINTS_BASE = 0.08
HINT_PENALTY_FACTOR = 0.02  # per hint level
WRONG_DELTA = -0.03
MIN_MASTERY = 0.0
MAX_MASTERY = 1.0


class MasteryService:
    """Manages per-user per-topic mastery values."""

    async def get_or_create(
        self, db: AsyncSession, user_id: str, topic: str
    ) -> LearningProgress:
        """Get existing progress or create a new one."""
        stmt = select(LearningProgress).where(
            and_(
                LearningProgress.user_id == user_id,
                LearningProgress.topic == topic,
            )
        )
        result = await db.execute(stmt)
        progress = result.scalar_one_or_none()

        if progress is None:
            progress = LearningProgress(
                user_id=user_id,
                topic=topic,
                mastery=0.0,
                problems_attempted=0,
                problems_completed=0,
                total_hints_used=0,
            )
            db.add(progress)
            await db.flush()

        return progress

    async def update_mastery(
        self,
        db: AsyncSession,
        user_id: str,
        topic: str,
        correct: bool,
        hint_level: int = 0,
        first_try: bool = False,
    ) -> LearningProgress:
        """Update mastery based on a student interaction."""
        progress = await self.get_or_create(db, user_id, topic)

        if correct:
            if first_try and hint_level == 0:
                delta = CORRECT_FIRST_TRY_DELTA
            else:
                delta = max(
                    CORRECT_WITH_HINTS_BASE - (hint_level * HINT_PENALTY_FACTOR),
                    0.02,
                )
        else:
            delta = WRONG_DELTA

        progress.mastery = max(
            MIN_MASTERY,
            min(MAX_MASTERY, progress.mastery + delta),
        )
        progress.total_hints_used += hint_level

        logger.info(
            f"Mastery update: user={user_id}, topic={topic}, "
            f"correct={correct}, hint_level={hint_level}, "
            f"delta={delta:+.3f}, new_mastery={progress.mastery:.3f}"
        )
        return progress

    async def record_problem_attempt(
        self, db: AsyncSession, user_id: str, topics: list, completed: bool = False
    ) -> None:
        """Record that a user attempted/completed a problem across its topics."""
        for topic in topics:
            progress = await self.get_or_create(db, user_id, topic)
            progress.problems_attempted += 1
            if completed:
                progress.problems_completed += 1

    async def get_user_progress(
        self, db: AsyncSession, user_id: str
    ) -> list:
        """Get all learning progress entries for a user."""
        stmt = (
            select(LearningProgress)
            .where(LearningProgress.user_id == user_id)
            .order_by(LearningProgress.topic)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())


# Default singleton
mastery_service = MasteryService()
