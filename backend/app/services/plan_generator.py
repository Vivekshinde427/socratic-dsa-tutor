from typing import Optional
from backend.app.config import settings
from backend.app.core.logging import logger
from backend.app.db.models.problem import Problem
from backend.app.schemas.tutoring_plan import ProblemSpec, TutoringPlan
from backend.app.services.llm.gemini_service import GeminiService, gemini_service
from backend.app.services.prompts.problem_analyst import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
)


class PlanGenerationService:
    def __init__(self, llm: Optional[GeminiService] = None):
        self.llm = llm or gemini_service

    async def generate_plan(
        self,
        problem: Problem,
    ) -> TutoringPlan:
        logger.info(f"Generating tutoring plan for problem '{problem.title}' (id={problem.id})")

        user_prompt = USER_PROMPT_TEMPLATE.format(
            title=problem.title,
            statement=problem.statement,
            difficulty=problem.difficulty,
            topics=", ".join(problem.topics) if problem.topics else "General DSA",
            constraints="\n".join(problem.constraints) if problem.constraints else "Standard bounds",
            examples=str(problem.examples) if problem.examples else "None provided",
        )

        plan = await self.llm.generate_structured(
            prompt=user_prompt,
            schema_class=TutoringPlan,
            system_instruction=SYSTEM_PROMPT,
        )

        # Enforce consistent metadata
        plan.prompt_version = PROMPT_VERSION
        plan.model_name = self.llm.model_name
        plan.problem.title = problem.title
        plan.problem.statement = problem.statement

        return plan


plan_generation_service = PlanGenerationService()
