"""
LangGraph Tutoring Workflow (SPEC §10, Diagram 1).
Implements the core Socratic tutoring loop:
START -> load_context -> route_intent ->
  [deflect] -> deflect -> guard -> END
  [start] -> present_step -> guard -> END
  [hint] -> further_guidance -> guard -> END
  [evaluate] -> evaluate ->
      understood?
        YES -> update_progress -> (if finished -> formative_feedback -> guard -> END, else -> present_step -> guard -> END)
        NO  -> further_guidance -> guard -> END
"""
from typing import Any, Dict, List, Optional, TypedDict
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END

from backend.app.core.logging import logger
from backend.app.schemas.session import (
    EvaluationClassification,
    EvaluationResult,
    MCQResultOut,
    TutorResponseType,
)
from backend.app.schemas.tutoring_plan import (
    ClientMCQOption,
    ClientStepDTO,
    Step,
    TutoringPlan,
)
from backend.app.services.leak_guard import leak_guard
from backend.app.services.evaluator import evaluator
from backend.app.services.hint_service import hint_service
from backend.app.services.mcq_service import mcq_service
from backend.app.services.prompts.tutor_prompts import (
    DEFLECTION_RESPONSE,
    FURTHER_GUIDANCE_SYSTEM_PROMPT,
    FURTHER_GUIDANCE_USER_TEMPLATE,
    FORMATIVE_FEEDBACK_SYSTEM_PROMPT,
    FORMATIVE_FEEDBACK_USER_TEMPLATE,
)
from backend.app.services.llm.gemini_service import gemini_service


class TutoringState(TypedDict, total=False):
    # Session / Identity
    session_id: str
    user_id: str
    problem_id: str
    problem_title: str
    problem_topics: List[str]

    # Plan & Step
    plan_dict: Optional[Dict[str, Any]]
    current_step_index: int
    current_hint_level: int
    attempts: int

    # Student input
    input_type: str  # "start", "mcq", "free_text", "hint"
    student_input: str
    selected_option_id: Optional[str]

    # Evaluation & Routing
    intent: str  # "start", "deflect", "hint", "evaluate"
    is_understood: bool
    evaluation: Optional[Dict[str, Any]]
    mcq_result: Optional[Dict[str, Any]]

    # Response to learner
    response_type: str
    response_message: str
    step_data: Optional[Dict[str, Any]]
    session_status: str
    stage_progress: Dict[str, str]

    # Guard
    guard_passed: bool
    guard_reason: str


# ── Helper to convert plan dict to schema ────────────────────────────

def _get_step_schema(state: TutoringState) -> Optional[Step]:
    plan_dict = state.get("plan_dict")
    if not plan_dict:
        return None
    # Support both "socratic_steps" and "steps"
    steps = plan_dict.get("socratic_steps") or plan_dict.get("steps") or []
    idx = state.get("current_step_index", 0)
    if 0 <= idx < len(steps):
        try:
            return Step.model_validate(steps[idx])
        except Exception as e:
            logger.warning(f"Failed to validate step {idx}: {e}")
            return None
    return None


def _build_client_step(step: Step, step_index: int) -> ClientStepDTO:
    """Build client-safe step DTO WITHOUT correct_option_id."""
    return ClientStepDTO.from_step(step)


# ── Node 1: load_context ─────────────────────────────────────────────

async def node_load_context(state: TutoringState, config: RunnableConfig) -> Dict[str, Any]:
    """Ensures context is initialized."""
    logger.info(f"[Graph] load_context: session={state.get('session_id')}, step={state.get('current_step_index')}")
    return {}


# ── Node 2: route_intent ─────────────────────────────────────────────

async def node_route_intent(state: TutoringState, config: RunnableConfig) -> Dict[str, Any]:
    """Classifies user intent for graph routing."""
    input_type = state.get("input_type", "free_text")
    text = state.get("student_input", "").strip().lower()

    if input_type == "start":
        return {"intent": "start"}

    if input_type == "hint":
        return {"intent": "hint"}

    # Check for solution requests or jailbreaks
    eval_check = evaluator._quick_pattern_check(text)
    if eval_check and eval_check.classification == EvaluationClassification.request_solution:
        return {"intent": "deflect"}

    if eval_check and eval_check.classification == EvaluationClassification.stuck:
        return {"intent": "hint"}

    return {"intent": "evaluate"}


# ── Node 3: present_step ─────────────────────────────────────────────

async def node_present_step(state: TutoringState, config: RunnableConfig) -> Dict[str, Any]:
    """Presents the current step question and MCQ options safely to the student."""
    step = _get_step_schema(state)
    step_idx = state.get("current_step_index", 0)

    if not step:
        return {
            "response_type": TutorResponseType.session_complete.value,
            "response_message": "Congratulations! You have completed all guided steps for this problem.",
            "session_status": "completed",
        }

    client_step = _build_client_step(step, step_idx)
    intro = f"Stage: {step.stage.value.replace('_', ' ').title()}.\n\n{step.question}"

    # Update stage progress map
    stage_progress = dict(state.get("stage_progress") or {})
    stage_progress[step.stage.value] = "ACTIVE"

    return {
        "response_type": TutorResponseType.mcq_step.value,
        "response_message": intro,
        "step_data": client_step.model_dump(),
        "stage_progress": stage_progress,
        "current_hint_level": 0,
        "attempts": 0,
    }


# ── Node 4: evaluate ─────────────────────────────────────────────────

async def node_evaluate(state: TutoringState, config: RunnableConfig) -> Dict[str, Any]:
    """Evaluates student's response (MCQ or free-text)."""
    step = _get_step_schema(state)
    if not step:
        return {"is_understood": True}

    input_type = state.get("input_type", "free_text")

    if input_type == "mcq":
        selected_id = (state.get("selected_option_id") or "").strip().upper()
        correct_id = step.correct_option_id.strip().upper()
        is_correct = (selected_id == correct_id)

        # Look in option_feedback list
        feedback = ""
        misconception_id = None
        for opt_fb in step.option_feedback:
            if opt_fb.option_id.strip().upper() == selected_id:
                feedback = opt_fb.why_wrong
                misconception_id = opt_fb.misconception_id
                break

        if not feedback:
            if is_correct:
                feedback = "Great job! That is the correct insight."
            else:
                feedback = "That's not quite right. Think carefully about the problem constraints."

        mcq_result = {
            "correct": is_correct,
            "selected_option_id": selected_id,
            "feedback": feedback,
            "misconception_id": misconception_id,
        }

        return {
            "is_understood": is_correct,
            "mcq_result": mcq_result,
            "attempts": state.get("attempts", 0) + 1,
        }

    else:
        # Free-text evaluation
        res = await evaluator.evaluate_free_text(
            problem_title=state.get("problem_title", ""),
            step=step,
            student_response=state.get("student_input", ""),
        )
        is_understood = (res.classification in (
            EvaluationClassification.correct,
            EvaluationClassification.partially_correct,
        ) and res.confidence >= 0.6)

        return {
            "is_understood": is_understood,
            "evaluation": res.model_dump(),
            "attempts": state.get("attempts", 0) + 1,
        }


# ── Node 5: further_guidance ─────────────────────────────────────────

async def node_further_guidance(state: TutoringState, config: RunnableConfig) -> Dict[str, Any]:
    """Provides targeted Socratic guidance, remediation, or hint escalation."""
    step = _get_step_schema(state)
    if not step:
        return {
            "response_type": TutorResponseType.free_text_response.value,
            "response_message": "Let's review the problem requirements once more.",
        }

    intent = state.get("intent", "")
    current_hint_level = state.get("current_hint_level", 0)

    # If this was an explicit hint request or stuck
    if intent == "hint":
        new_hint_level = min(current_hint_level + 1, 4)
        _, hint_text = hint_service.get_hint_for_step(step, new_hint_level)
        return {
            "response_type": TutorResponseType.hint.value,
            "response_message": f"💡 Hint (Level {new_hint_level}): {hint_text}",
            "current_hint_level": new_hint_level,
        }

    # If MCQ was answered incorrectly
    mcq_result = state.get("mcq_result")
    if mcq_result and not mcq_result.get("correct"):
        feedback = mcq_result.get("feedback") or "Not quite."
        # Escalate hint level on wrong answer
        new_hint_level = min(current_hint_level + 1, 4)
        _, hint_text = hint_service.get_hint_for_step(step, new_hint_level)
        msg = f"{feedback}\n\n💡 Consider this hint: {hint_text}"
        return {
            "response_type": TutorResponseType.mcq_result.value,
            "response_message": msg,
            "current_hint_level": new_hint_level,
        }

    # Free-text incorrect: use LLM remediation
    student_resp = state.get("student_input", "")
    eval_dict = state.get("evaluation") or {}
    new_hint_level = min(current_hint_level + 1, 4)

    if gemini_service.api_key:
        try:
            prompt = FURTHER_GUIDANCE_USER_TEMPLATE.format(
                problem_title=state.get("problem_title", ""),
                current_stage=step.stage.value,
                current_question=step.question,
                student_response=student_resp,
                evaluation_summary=eval_dict.get("evidence", ""),
                misconception_description=eval_dict.get("missing_concept", ""),
                hint_level=new_hint_level,
            )
            guidance = await gemini_service.generate_text(
                prompt=prompt,
                system_instruction=FURTHER_GUIDANCE_SYSTEM_PROMPT,
                temperature=0.3,
            )
            return {
                "response_type": TutorResponseType.free_text_response.value,
                "response_message": guidance.strip(),
                "current_hint_level": new_hint_level,
            }
        except Exception as e:
            logger.warning(f"Remediation LLM failed: {e}")

    # Fallback remediation
    _, hint_text = hint_service.get_hint_for_step(step, new_hint_level)
    return {
        "response_type": TutorResponseType.free_text_response.value,
        "response_message": f"You're making progress, but think about this: {hint_text}",
        "current_hint_level": new_hint_level,
    }


# ── Node 6: update_progress ──────────────────────────────────────────

async def node_update_progress(state: TutoringState, config: RunnableConfig) -> Dict[str, Any]:
    """Advances stage progress when student demonstrates understanding."""
    step = _get_step_schema(state)
    step_idx = state.get("current_step_index", 0)
    stage_progress = dict(state.get("stage_progress") or {})

    if step:
        stage_progress[step.stage.value] = "COMPLETED"

    next_step_idx = step_idx + 1
    plan_dict = state.get("plan_dict") or {}
    steps = plan_dict.get("socratic_steps") or plan_dict.get("steps") or []
    total_steps = len(steps)

    is_complete = next_step_idx >= total_steps
    session_status = "completed" if is_complete else "active"

    return {
        "current_step_index": next_step_idx,
        "current_hint_level": 0,
        "stage_progress": stage_progress,
        "session_status": session_status,
        "response_type": TutorResponseType.stage_advance.value,
    }


# ── Node 7: formative_feedback ───────────────────────────────────────

async def node_formative_feedback(state: TutoringState, config: RunnableConfig) -> Dict[str, Any]:
    """Generates formative feedback upon completing all stages."""
    completed_stages = [k for k, v in (state.get("stage_progress") or {}).items() if v == "COMPLETED"]

    if gemini_service.api_key:
        try:
            prompt = FORMATIVE_FEEDBACK_USER_TEMPLATE.format(
                problem_title=state.get("problem_title", ""),
                stages_completed=", ".join(completed_stages),
                total_hints=state.get("current_hint_level", 0),
                total_attempts=state.get("attempts", 0),
                topics=", ".join(state.get("problem_topics", [])),
            )
            feedback = await gemini_service.generate_text(
                prompt=prompt,
                system_instruction=FORMATIVE_FEEDBACK_SYSTEM_PROMPT,
                temperature=0.4,
            )
            return {
                "response_type": TutorResponseType.formative_feedback.value,
                "response_message": f"🎉 Excellent work!\n\n{feedback.strip()}",
                "session_status": "completed",
            }
        except Exception as e:
            logger.warning(f"Formative feedback LLM failed: {e}")

    # Fallback formative feedback
    return {
        "response_type": TutorResponseType.formative_feedback.value,
        "response_message": (
            "🎉 Excellent work! You have successfully walked through the conceptual foundations, "
            "analyzed the problem bottleneck, identified the optimal pattern, and verified complexity. "
            "You are now ready to implement the code solution!"
        ),
        "session_status": "completed",
    }


# ── Node 8: deflect ──────────────────────────────────────────────────

async def node_deflect(state: TutoringState, config: RunnableConfig) -> Dict[str, Any]:
    """Deflects direct requests for answers/code while encouraging Socratic discovery."""
    return {
        "response_type": TutorResponseType.deflection.value,
        "response_message": DEFLECTION_RESPONSE,
    }


# ── Node 9: guard ────────────────────────────────────────────────────

async def node_guard(state: TutoringState, config: RunnableConfig) -> Dict[str, Any]:
    """Validates the learner-facing message through Leak Guard before exposure."""
    message = state.get("response_message", "")
    if not message:
        return {"guard_passed": True}

    plan_dict = state.get("plan_dict") or {}
    ref_sol = plan_dict.get("reference_solution", {})
    ref_code = ref_sol.get("code", "") if isinstance(ref_sol, dict) else str(ref_sol)
    title = state.get("problem_title", "")
    step = _get_step_schema(state)
    stage = step.stage.value if step else ""

    result = await leak_guard.check(
        response=message,
        reference_code=ref_code,
        problem_title=title,
        current_stage=stage,
    )

    if not result.safe:
        logger.warning(f"[Graph Guard] Blocked unsafe message: {result.reason}")
        safe_fallback = (
            "Let's focus on the key concepts for this step. "
            "What do you think is the main constraint or invariant we should track?"
        )
        return {
            "response_message": safe_fallback,
            "guard_passed": False,
            "guard_reason": result.reason,
        }

    return {"guard_passed": True}


# ── Conditional Edge Functions ───────────────────────────────────────

def route_after_intent(state: TutoringState) -> str:
    intent = state.get("intent", "evaluate")
    if intent == "start":
        return "present_step"
    if intent == "deflect":
        return "deflect"
    if intent == "hint":
        return "further_guidance"
    return "evaluate"


def route_after_evaluation(state: TutoringState) -> str:
    if state.get("is_understood", False):
        return "update_progress"
    return "further_guidance"


def route_after_progress(state: TutoringState) -> str:
    if state.get("session_status") == "completed":
        return "formative_feedback"
    return "present_step"


# ── Build and Compile Graph ──────────────────────────────────────────

def build_tutoring_graph():
    workflow = StateGraph(TutoringState)

    # Add all nodes
    workflow.add_node("load_context", node_load_context)
    workflow.add_node("route_intent", node_route_intent)
    workflow.add_node("present_step", node_present_step)
    workflow.add_node("evaluate", node_evaluate)
    workflow.add_node("further_guidance", node_further_guidance)
    workflow.add_node("update_progress", node_update_progress)
    workflow.add_node("formative_feedback", node_formative_feedback)
    workflow.add_node("deflect", node_deflect)
    workflow.add_node("guard", node_guard)

    # Edges
    workflow.add_edge(START, "load_context")
    workflow.add_edge("load_context", "route_intent")

    workflow.add_conditional_edges(
        "route_intent",
        route_after_intent,
        {
            "present_step": "present_step",
            "deflect": "deflect",
            "further_guidance": "further_guidance",
            "evaluate": "evaluate",
        },
    )

    workflow.add_conditional_edges(
        "evaluate",
        route_after_evaluation,
        {
            "update_progress": "update_progress",
            "further_guidance": "further_guidance",
        },
    )

    workflow.add_conditional_edges(
        "update_progress",
        route_after_progress,
        {
            "formative_feedback": "formative_feedback",
            "present_step": "present_step",
        },
    )

    workflow.add_edge("deflect", "guard")
    workflow.add_edge("further_guidance", "guard")
    workflow.add_edge("present_step", "guard")
    workflow.add_edge("formative_feedback", "guard")
    workflow.add_edge("guard", END)

    return workflow.compile()


tutoring_graph = build_tutoring_graph()
