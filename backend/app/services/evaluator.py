"""
Free-text response evaluation service.
Evaluates student text responses against learning objectives and rubrics using LLM.
Returns structured EvaluationResult for graph routing.
"""
import json
import re
from typing import Optional

from backend.app.core.logging import logger
from backend.app.schemas.session import EvaluationClassification, EvaluationResult
from backend.app.schemas.tutoring_plan import Step
from backend.app.services.llm.gemini_service import GeminiService, gemini_service
from backend.app.services.prompts.tutor_prompts import (
    FREE_TEXT_EVAL_SYSTEM_PROMPT,
    FREE_TEXT_EVAL_USER_TEMPLATE,
)


# Solution-seeking keywords for fast deflection routing
SOLUTION_REQUEST_PATTERNS = [
    r"\b(give\s+me|tell\s+me|show\s+me|what\s+is)\s+(the\s+)?(full\s+|complete\s+)?(code|solution|answer)\b",
    r"\bjust\s+(give|tell|write)\s+(me\s+)?(the\s+)?(code|solution|answer)\b",
    r"\bsolve\s+it\s+for\s+me\b",
    r"\bcan\s+you\s+(write|give)\s+(me\s+)?(the\s+)?code\b",
]

# Stuck keywords
STUCK_PATTERNS = [
    r"^(i\s+don'?t\s+know|idk|i'?m\s+stuck|stuck|help\s*me?|no\s+idea|confused)\.?$",
]


class Evaluator:
    """Evaluates student free-text responses against Socratic objectives."""

    def __init__(self, llm: Optional[GeminiService] = None):
        self.llm = llm or gemini_service

    def _quick_pattern_check(self, text: str) -> Optional[EvaluationResult]:
        """Fast regex check for solution requests or stuck responses before invoking LLM."""
        cleaned = text.strip().lower()

        for pattern in SOLUTION_REQUEST_PATTERNS:
            if re.search(pattern, cleaned):
                return EvaluationResult(
                    classification=EvaluationClassification.request_solution,
                    confidence=0.95,
                    evidence="Student explicitly asked for code or full solution.",
                    missing_concept="",
                )

        for pattern in STUCK_PATTERNS:
            if re.search(pattern, cleaned):
                return EvaluationResult(
                    classification=EvaluationClassification.stuck,
                    confidence=0.95,
                    evidence="Student indicated they are stuck.",
                    missing_concept="",
                )

        return None

    async def evaluate_free_text(
        self,
        problem_title: str,
        step: Step,
        student_response: str,
    ) -> EvaluationResult:
        """
        Evaluate student's free text response.
        Returns structured EvaluationResult for routing.
        """
        # Fast regex pre-checks
        quick_match = self._quick_pattern_check(student_response)
        if quick_match:
            return quick_match

        # If LLM key is not configured (e.g. offline tests), use heuristic fallback
        if not self.llm.api_key:
            return self._heuristic_fallback(step, student_response)

        try:
            success_str = ", ".join(step.success_criteria) if step.success_criteria else ""
            prompt = FREE_TEXT_EVAL_USER_TEMPLATE.format(
                problem_title=problem_title,
                current_stage=step.stage.value,
                current_question=step.question,
                success_criteria=success_str,
                student_response=student_response,
            )

            raw = await self.llm.generate_text(
                prompt=prompt,
                system_instruction=FREE_TEXT_EVAL_SYSTEM_PROMPT,
                temperature=0.0,
            )

            cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
            cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
            data = json.loads(cleaned)

            classification_str = data.get("classification", "partially_correct")
            try:
                classification = EvaluationClassification(classification_str)
            except ValueError:
                classification = EvaluationClassification.partially_correct

            return EvaluationResult(
                classification=classification,
                confidence=float(data.get("confidence", 0.7)),
                misconception_id=data.get("misconception_id"),
                evidence=str(data.get("evidence", "")),
                missing_concept=str(data.get("missing_concept", "")),
            )
        except Exception as e:
            logger.warning(f"LLM free-text evaluation failed: {e}. Using fallback.")
            return self._heuristic_fallback(step, student_response)

    def _heuristic_fallback(
        self, step: Step, student_response: str
    ) -> EvaluationResult:
        """Heuristic evaluation when LLM is unavailable."""
        text = student_response.lower().strip()
        criteria = " ".join(step.success_criteria).lower()

        # Check keyword overlap with success criteria
        criteria_words = set(re.findall(r"\w+", criteria))
        response_words = set(re.findall(r"\w+", text))
        overlap = len(criteria_words & response_words)

        if overlap >= 2 or len(text) > 40:
            return EvaluationResult(
                classification=EvaluationClassification.correct,
                confidence=0.7,
                evidence="Response contains relevant keywords matching success criteria.",
            )
        else:
            return EvaluationResult(
                classification=EvaluationClassification.partially_correct,
                confidence=0.5,
                evidence="Heuristic evaluation: response partially addresses the concept.",
                missing_concept="More depth required.",
            )


evaluator = Evaluator()
