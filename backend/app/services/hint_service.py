"""
Hint Service (SPEC §10, Diagram 1).
Manages hint ladder escalation (Levels 1-4) with persistence.
Level 1: Conceptual nudge
Level 2: Leading question
Level 3: Concrete example / invariant
Level 4: Partial pseudocode / code scaffold with blanks (NEVER full code)
"""
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import logger
from backend.app.db.models.session import Session
from backend.app.schemas.tutoring_plan import Step

MAX_HINT_LEVEL = 4


class HintService:
    """Manages hint retrieval and escalation for tutoring steps."""

    def get_hint_for_step(
        self,
        step: Step,
        requested_level: int,
    ) -> Tuple[int, str]:
        """
        Get the hint text for a step at the requested level (1-4).
        Clamps to [1, 4]. Ensures Level 4 has gaps/blanks and NEVER leaks full code.
        """
        level = max(1, min(requested_level, MAX_HINT_LEVEL))

        # Look for explicit hint with matching level in hint_ladder
        hint_text = None
        if step.hint_ladder:
            matched = next((h for h in step.hint_ladder if h.level == level), None)
            if matched:
                hint_text = matched.content
            elif level - 1 < len(step.hint_ladder):
                hint_text = step.hint_ladder[level - 1].content

        if not hint_text:
            # Fallback if step doesn't have 4 hints configured
            fallbacks = {
                1: f"Consider what information you need at this stage: {step.question}",
                2: "Think about the simplest small example. What pattern do you notice?",
                3: "Try tracing through with small values to test your intuition.",
                4: "Here is the scaffold with missing parts:\nfor x in items:\n    # check invariant\n    if ___ in seen:\n        return [___, x]\n    seen.add(___)",
            }
            hint_text = fallbacks.get(level, "Think about the problem constraints and what you have learned.")

        # Safety check: if level 4, verify it doesn't give a full working solution
        if level == 4 and "def " in hint_text and "return" in hint_text and "___" not in hint_text:
            hint_text = hint_text.replace("return", "# fill in return\n        ___")

        return level, hint_text

    async def escalate_hint(
        self,
        db: AsyncSession,
        session: Session,
        step: Step,
    ) -> Tuple[int, str]:
        """
        Escalates session hint level by 1 (up to MAX_HINT_LEVEL),
        persists the new level to the session, and returns (level, hint_text).
        """
        new_level = min(session.current_hint_level + 1, MAX_HINT_LEVEL)
        session.current_hint_level = new_level
        await db.flush()

        logger.info(
            f"Hint escalated: session={session.id}, step={session.current_step_index}, "
            f"new_level={new_level}"
        )

        return self.get_hint_for_step(step, new_level)


hint_service = HintService()
