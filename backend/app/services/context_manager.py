"""
Context Management Service (SPEC §11, Diagram 2).
Assembles contextual information for LLM tutor prompts:
- Problem metadata
- Current stage & step info
- Recent 6-8 conversation turns
- Rolling summary
- Learner progress / mastery
- Hints already consumed
Drops redundant or stale content.
"""
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import logger
from backend.app.db.models.message import Message
from backend.app.db.models.problem import Problem
from backend.app.db.models.session import Session
from backend.app.schemas.tutoring_plan import TutoringPlan, Step
from backend.app.services.mastery_service import mastery_service
from backend.app.services.llm.gemini_service import GeminiService, gemini_service


SUMMARY_UPDATE_INTERVAL = 6  # Update rolling summary every 6 turns


class ContextManager:
    """Manages context assembly and rolling summary maintenance."""

    def __init__(self, llm: Optional[GeminiService] = None):
        self.llm = llm or gemini_service

    async def assemble_context(
        self,
        db: AsyncSession,
        session: Session,
        problem: Problem,
        plan: Optional[TutoringPlan],
        current_step: Optional[Step],
        recent_messages: List[Message],
        query: str = "",
    ) -> Dict[str, Any]:
        """Assemble the complete context packet for the tutoring engine."""
        # Get mastery across problem topics
        topics = problem.topics or []
        user_progress = await mastery_service.get_user_progress(db, session.user_id)
        topic_mastery = {
            p.topic: round(p.mastery, 2)
            for p in user_progress
            if p.topic in topics
        }

        # Format recent turns (role: content)
        turns = []
        for msg in recent_messages[-8:]:  # Last 6-8 turns max
            turns.append({
                "role": msg.role,
                "content": msg.content,
                "type": msg.message_type,
            })

        current_stage = current_step.stage.value if current_step else "understand"
        question_text = current_step.question if current_step else ""
        success_criteria = ", ".join(current_step.success_criteria) if current_step and current_step.success_criteria else ""

        return {
            "session_id": session.id,
            "problem_id": problem.id,
            "problem_title": problem.title,
            "difficulty": problem.difficulty,
            "topics": topics,
            "current_stage": current_stage,
            "step_index": session.current_step_index,
            "hint_level": session.current_hint_level,
            "current_question": question_text,
            "success_criteria": success_criteria,
            "rolling_summary": session.rolling_summary or "Session started.",
            "recent_turns": turns,
            "topic_mastery": topic_mastery,
            "stage_progress": session.stage_progress or {},
            "student_query": query,
        }

    async def maybe_update_rolling_summary(
        self,
        db: AsyncSession,
        session: Session,
        messages: List[Message],
    ) -> None:
        """Update rolling summary if turn count warrants it."""
        if len(messages) < SUMMARY_UPDATE_INTERVAL:
            return

        # Check if we should summarize
        if len(messages) % SUMMARY_UPDATE_INTERVAL != 0:
            return

        if not self.llm.api_key:
            # Fallback simple summary when no LLM key
            last_msgs = [f"{m.role}: {m.content[:60]}" for m in messages[-4:]]
            session.rolling_summary = "Recent discussion: " + " | ".join(last_msgs)
            return

        try:
            conversation_text = "\n".join(
                f"{m.role}: {m.content}" for m in messages[-SUMMARY_UPDATE_INTERVAL:]
            )
            prompt = (
                f"Previous summary: {session.rolling_summary}\n\n"
                f"Recent conversation turns:\n{conversation_text}\n\n"
                "Provide an updated 2-3 sentence rolling summary of the student's conceptual progress, "
                "struggles, and key insights so far. Focus on what was understood or misunderstood. "
                "Do NOT include solution code."
            )
            summary = await self.llm.generate_text(
                prompt=prompt,
                system_instruction="You are a concise educational progress summarizer.",
                temperature=0.2,
            )
            session.rolling_summary = summary.strip()
            logger.info(f"Updated rolling summary for session {session.id}")
        except Exception as e:
            logger.warning(f"Failed to update rolling summary: {e}")


context_manager = ContextManager()
