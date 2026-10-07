import os
import pytest

from backend.app.config import settings
from backend.app.schemas.tutoring_plan import Difficulty, Example, ProblemSpec, TutoringPlan
from backend.app.services.llm.gemini_service import GeminiService
from backend.app.services.plan_generator import PlanGenerationService
from backend.app.db.models.problem import Problem


@pytest.mark.skipif(
    not bool(settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")),
    reason="GEMINI_API_KEY is not configured; skipping live provider smoke test.",
)
@pytest.mark.asyncio
async def test_live_gemini_plan_generation():
    service = GeminiService()
    generator = PlanGenerationService(llm=service)

    test_problem = Problem(
        id="live-test-prob",
        title="Valid Anagram",
        slug="valid-anagram",
        statement="Given two strings s and t, return true if t is an anagram of s, and false otherwise.",
        difficulty="easy",
        topics=["String", "Hash Table"],
        constraints=["1 <= s.length, t.length <= 5 * 10^4"],
        examples=[{"input": '"anagram", "nagaram"', "output": "true", "explanation": ""}],
        source="seed",
    )

    plan = await generator.generate_plan(test_problem)

    assert isinstance(plan, TutoringPlan)
    assert plan.problem.title == "Valid Anagram"
    assert len(plan.socratic_steps) > 0
    assert plan.reference_solution.code != ""
    assert plan.brute_force_solution.code != ""
    assert len(plan.test_cases) > 0
