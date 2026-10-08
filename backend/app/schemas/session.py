"""Schemas for tutoring sessions, messages, and tutor interactions."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.tutoring_plan import (
    ClientMCQOption,
    ClientStepDTO,
    SocraticStage,
)


# ── Session schemas ──────────────────────────────────────────────

class SessionCreate(BaseModel):
    problem_id: str


class SessionStatus(str, Enum):
    active = "active"
    completed = "completed"
    abandoned = "abandoned"


class StageStatus(str, Enum):
    locked = "LOCKED"
    active = "ACTIVE"
    under_review = "UNDER_REVIEW"
    completed = "COMPLETED"
    needs_revisit = "NEEDS_REVISIT"


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    problem_id: str
    status: str
    current_step_index: int
    current_hint_level: int
    stage_progress: Dict[str, str]
    created_at: datetime
    updated_at: datetime


class SessionDetail(SessionOut):
    rolling_summary: str = ""
    plan_id: Optional[str] = None


# ── Message schemas ──────────────────────────────────────────────

class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    role: str
    content: str
    message_type: str
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    step_index: Optional[int] = None
    created_at: datetime


# ── Student interaction request schemas ──────────────────────────

class MCQAnswerRequest(BaseModel):
    """Student submits an MCQ answer."""
    selected_option_id: str


class FreeTextRequest(BaseModel):
    """Student submits a free-text response."""
    content: str = Field(..., min_length=1, max_length=5000)


class HintRequest(BaseModel):
    """Student requests a hint ('I'm stuck')."""
    pass  # No body needed


class SolutionRequestFlag(str, Enum):
    """Detected intent types for deflection."""
    request_solution = "request_solution"
    jailbreak = "jailbreak"
    off_topic = "off_topic"


# ── Tutor response schemas ──────────────────────────────────────

class TutorResponseType(str, Enum):
    mcq_step = "mcq_step"
    mcq_result = "mcq_result"
    free_text_response = "free_text_response"
    hint = "hint"
    formative_feedback = "formative_feedback"
    deflection = "deflection"
    stage_advance = "stage_advance"
    session_complete = "session_complete"
    error = "error"


class MCQResultOut(BaseModel):
    correct: bool
    selected_option_id: str
    feedback: str = ""
    misconception_id: Optional[str] = None


class EvaluationClassification(str, Enum):
    correct = "correct"
    partially_correct = "partially_correct"
    misconception = "misconception"
    incorrect = "incorrect"
    stuck = "stuck"
    irrelevant = "irrelevant"
    request_solution = "request_solution"
    off_topic = "off_topic"


class EvaluationResult(BaseModel):
    classification: EvaluationClassification
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    misconception_id: Optional[str] = None
    evidence: str = ""
    missing_concept: str = ""


class TutorResponse(BaseModel):
    """Unified tutor response sent to the client."""
    response_type: TutorResponseType
    message: str = ""
    # MCQ step data (when presenting a new step)
    step: Optional[ClientStepDTO] = None
    # MCQ result (when evaluating an answer)
    mcq_result: Optional[MCQResultOut] = None
    # Current position info
    current_step_index: int = 0
    current_stage: Optional[SocraticStage] = None
    hint_level: int = 0
    # Stage progress map
    stage_progress: Dict[str, str] = Field(default_factory=dict)
    # Session status
    session_status: str = "active"


# ── Code execution schemas ───────────────────────────────────────

class CodeRunRequest(BaseModel):
    language: str = "python"
    code: str = Field(..., min_length=1, max_length=50000)


class CodeRunResultOut(BaseModel):
    status: str
    stdout: str = ""
    stderr: str = ""
    execution_time_ms: float = 0.0
    tests_passed: Optional[int] = None
    tests_total: Optional[int] = None
    test_results: Dict[str, Any] = Field(default_factory=dict)


# ── Progress schemas ─────────────────────────────────────────────

class LearningProgressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    topic: str
    mastery: float
    problems_attempted: int
    problems_completed: int
    total_hints_used: int
    updated_at: datetime
