from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class Difficulty(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class VerificationStatus(str, Enum):
    unverified = "unverified"
    verified = "verified"
    verification_failed = "verification_failed"


class SocraticStage(str, Enum):
    understand = "understand"
    examples_edges = "examples_edges"
    brute_force = "brute_force"
    bottleneck = "bottleneck"
    pattern_data_structure = "pattern_data_structure"
    algorithm_design = "algorithm_design"
    complexity = "complexity"
    implementation = "implementation"
    reflection = "reflection"


class Example(BaseModel):
    input: str
    output: str
    explanation: str = ""


class Approach(BaseModel):
    idea: str
    time_complexity: str
    space_complexity: str
    why_it_works: str


class SolutionCode(BaseModel):
    language: str = "python"
    code: str


class TestCaseCategory(str, Enum):
    __test__ = False
    sample = "sample"
    edge = "edge"
    random = "random"
    adversarial = "adversarial"


class TestCase(BaseModel):
    __test__ = False
    input: str
    expected_output: str
    category: TestCaseCategory = TestCaseCategory.sample


class Misconception(BaseModel):
    id: str
    description: str
    remediation_goal: str


class MCQOption(BaseModel):
    id: str
    text: str


class OptionFeedback(BaseModel):
    option_id: str
    misconception_id: Optional[str] = None
    why_wrong: str


class Hint(BaseModel):
    level: int = Field(ge=0, le=4)
    content: str


class Step(BaseModel):
    id: str
    stage: SocraticStage
    question: str
    options: List[MCQOption]
    correct_option_id: str  # Server-only: never expose to client
    option_feedback: List[OptionFeedback] = Field(default_factory=list)  # Server-only
    hint_ladder: List[Hint] = Field(default_factory=list)
    success_criteria: List[str] = Field(default_factory=list)

    @field_validator("options")
    @classmethod
    def validate_options(cls, v: List[MCQOption]) -> List[MCQOption]:
        if len(v) < 2:
            raise ValueError("A step must provide at least 2 options")
        return v

    @field_validator("correct_option_id")
    @classmethod
    def validate_correct_option(cls, v: str, info) -> str:
        options = info.data.get("options", [])
        if options and v not in [opt.id for opt in options]:
            raise ValueError(f"correct_option_id '{v}' must be one of the option IDs")
        return v


class ProblemSpec(BaseModel):
    title: str
    statement: str
    constraints: List[str] = Field(default_factory=list)
    examples: List[Example] = Field(default_factory=list)
    difficulty: Difficulty = Difficulty.easy
    topics: List[str] = Field(default_factory=list)


class Approaches(BaseModel):
    brute_force: Approach
    better: Optional[Approach] = None
    optimal: Approach


class TutoringPlan(BaseModel):
    plan_version: str = "1.0.0"
    problem: ProblemSpec
    pattern: str  # Server-only / hidden until appropriate stage
    prerequisites: List[str] = Field(default_factory=list)
    approaches: Approaches
    reference_solution: SolutionCode  # Server-only
    brute_force_solution: SolutionCode  # Server-only
    test_cases: List[TestCase] = Field(default_factory=list)  # Server-only expected outputs
    socratic_steps: List[Step]
    misconceptions: List[Misconception] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    verified: bool = False
    verification_status: VerificationStatus = VerificationStatus.unverified
    verification_notes: Optional[str] = None
    model_name: str = "gemini-2.5-flash"
    prompt_version: str = "1.0.0"


# -------------------------------------------------------------
# Client-Safe DTOs (Strictly sanitized - No leaks to browser)
# -------------------------------------------------------------

class ClientMCQOption(BaseModel):
    id: str
    text: str


class ClientStepDTO(BaseModel):
    id: str
    stage: SocraticStage
    question: str
    options: List[ClientMCQOption]
    hint_count: int = 0
    success_criteria: List[str] = Field(default_factory=list)

    @classmethod
    def from_step(cls, step: Step) -> "ClientStepDTO":
        return cls(
            id=step.id,
            stage=step.stage,
            question=step.question,
            options=[ClientMCQOption(id=opt.id, text=opt.text) for opt in step.options],
            hint_count=len(step.hint_ladder),
            success_criteria=step.success_criteria,
        )


class ClientProblemDTO(BaseModel):
    title: str
    statement: str
    constraints: List[str]
    examples: List[Example]
    difficulty: Difficulty
    topics: List[str]


class ClientPlanOverviewDTO(BaseModel):
    problem: ClientProblemDTO
    total_steps: int
    stages: List[SocraticStage]
    verified: bool
    verification_status: VerificationStatus
