from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.tutoring_plan import (
    Difficulty,
    Example,
    VerificationStatus,
    ClientProblemDTO,
)


class ProblemPasteRequest(BaseModel):
    title: Optional[str] = None
    statement: str = Field(..., min_length=10)


class ProblemCreate(BaseModel):
    title: str
    statement: str
    difficulty: Difficulty = Difficulty.easy
    topics: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    examples: List[Example] = Field(default_factory=list)
    source: str = "custom"


class ProblemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    slug: str
    difficulty: Difficulty
    topics: List[str]
    source: str
    created_at: datetime
    updated_at: datetime


class ProblemDetailOut(ProblemOut):
    statement: str
    constraints: List[str]
    examples: List[Example]
    has_plan: bool = False
    plan_verified: bool = False
    verification_status: Optional[VerificationStatus] = None


class PlanVerificationResponse(BaseModel):
    problem_id: str
    verified: bool
    verification_status: VerificationStatus
    notes: Optional[str] = None
