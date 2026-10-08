"""
MCQ grading service.
Performs deterministic server-side grading of student MCQ choices.
CRITICAL: Never expose correct_option_id to the client.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import logger
from backend.app.db.models.mcq_attempt import MCQAttempt
from backend.app.db.models.session import Session
from backend.app.schemas.session import MCQResultOut
from backend.app.schemas.tutoring_plan import Step


class MCQService:
    """Deterministic server-side grading for MCQ steps."""

    async def evaluate_answer(
        self,
        db: AsyncSession,
        session: Session,
        step: Step,
        selected_option_id: str,
    ) -> MCQResultOut:
        """
        Grades student answer against step.correct_option_id.
        Returns MCQResultOut WITHOUT leaking correct_option_id.
        """
        sel_id = selected_option_id.strip().upper()
        corr_id = step.correct_option_id.strip().upper()
        is_correct = (sel_id == corr_id)

        feedback = ""
        misconception_id = None

        # Look in option_feedback list
        opt_fb = next(
            (fb for fb in step.option_feedback if fb.option_id.strip().upper() == sel_id),
            None,
        )
        if opt_fb:
            feedback = opt_fb.why_wrong
            misconception_id = opt_fb.misconception_id

        if not feedback:
            if is_correct:
                feedback = "Great job! That is the correct insight."
            else:
                feedback = "That's not quite right. Think carefully about the problem constraints."

        # Record attempt in DB
        attempt = MCQAttempt(
            session_id=session.id,
            step_id=step.id,
            step_index=session.current_step_index,
            selected_option_id=sel_id,
            correct=is_correct,
            misconception_id=misconception_id,
            hint_level_at_attempt=session.current_hint_level,
        )
        db.add(attempt)
        await db.flush()

        logger.info(
            f"MCQ evaluated: session={session.id}, step={session.current_step_index}, "
            f"selected={sel_id}, correct={is_correct}"
        )

        return MCQResultOut(
            correct=is_correct,
            selected_option_id=sel_id,
            feedback=feedback,
            misconception_id=misconception_id,
        )


mcq_service = MCQService()
