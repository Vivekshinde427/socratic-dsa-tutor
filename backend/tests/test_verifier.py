import pytest

from backend.app.schemas.tutoring_plan import (
    Approach,
    Approaches,
    Difficulty,
    Example,
    MCQOption,
    ProblemSpec,
    SocraticStage,
    SolutionCode,
    Step,
    TestCase,
    TestCaseCategory,
    TutoringPlan,
    VerificationStatus,
)
from backend.app.services.verifier import PlanVerifier


def build_plan_with_solutions(ref_code: str, bf_code: str) -> TutoringPlan:
    step = Step(
        id="s1",
        stage=SocraticStage.understand,
        question="What is the goal?",
        options=[
            MCQOption(id="A", text="Find two indices that sum to target"),
            MCQOption(id="B", text="Find three indices"),
        ],
        correct_option_id="A",
    )
    return TutoringPlan(
        plan_version="1.0.0",
        problem=ProblemSpec(
            title="Two Sum Problem",
            statement="Find two numbers adding to target.",
            constraints=[],
            examples=[Example(input="[2, 7], 9", output="[0, 1]")],
            difficulty=Difficulty.easy,
            topics=["Array"],
        ),
        pattern="Hash Map Complement",
        prerequisites=[],
        approaches=Approaches(
            brute_force=Approach(
                idea="Nested loops",
                time_complexity="O(n^2)",
                space_complexity="O(1)",
                why_it_works="All pairs",
            ),
            optimal=Approach(
                idea="Hash map",
                time_complexity="O(n)",
                space_complexity="O(n)",
                why_it_works="Direct lookup",
            ),
        ),
        reference_solution=SolutionCode(language="python", code=ref_code),
        brute_force_solution=SolutionCode(language="python", code=bf_code),
        test_cases=[
            TestCase(input="[2, 7, 11, 15], 9", expected_output="[0, 1]"),
            TestCase(input="[3, 2, 4], 6", expected_output="[1, 2]"),
            TestCase(input="[3, 3], 6", expected_output="[0, 1]"),
        ],
        socratic_steps=[step],
        misconceptions=[],
        confidence=1.0,
        verified=False,
        verification_status=VerificationStatus.unverified,
        model_name="test-model",
        prompt_version="1.0.0",
    )


VALID_REF_CODE = """
def solve(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        comp = target - num
        if comp in seen:
            return [seen[comp], i]
        seen[num] = i
    return []
"""

VALID_BF_CODE = """
def solve(nums, target):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []
"""

WRONG_OUTPUT_CODE = """
def solve(nums, target):
    # Deliberately incorrect logic
    return [0, 0]
"""

SYNTAX_ERROR_CODE = """
def solve(nums, target)
    invalid syntax here
"""

RUNTIME_ERROR_CODE = """
def solve(nums, target):
    raise RuntimeError("Intentional crash during execution")
"""


@pytest.fixture
def verifier():
    return PlanVerifier()


@pytest.mark.asyncio
async def test_verifier_passes_valid_plan(verifier: PlanVerifier):
    plan = build_plan_with_solutions(VALID_REF_CODE, VALID_BF_CODE)
    result = await verifier.verify_plan(plan)

    assert result.verified is True
    assert result.status == VerificationStatus.verified
    assert plan.verified is True
    assert plan.verification_status == VerificationStatus.verified
    assert len(result.test_results) == 3
    assert all(tr.passed for tr in result.test_results)


@pytest.mark.asyncio
async def test_verifier_rejects_wrong_output(verifier: PlanVerifier):
    plan = build_plan_with_solutions(WRONG_OUTPUT_CODE, VALID_BF_CODE)
    result = await verifier.verify_plan(plan)

    assert result.verified is False
    assert result.status == VerificationStatus.verification_failed
    assert plan.verified is False
    assert plan.verification_status == VerificationStatus.verification_failed
    assert "Output mismatch" in result.notes


@pytest.mark.asyncio
async def test_verifier_rejects_syntax_error(verifier: PlanVerifier):
    plan = build_plan_with_solutions(SYNTAX_ERROR_CODE, VALID_BF_CODE)
    result = await verifier.verify_plan(plan)

    assert result.verified is False
    assert result.status == VerificationStatus.verification_failed
    assert plan.verified is False
    assert "failed on test case" in result.notes


@pytest.mark.asyncio
async def test_verifier_rejects_runtime_error(verifier: PlanVerifier):
    plan = build_plan_with_solutions(RUNTIME_ERROR_CODE, VALID_BF_CODE)
    result = await verifier.verify_plan(plan)

    assert result.verified is False
    assert result.status == VerificationStatus.verification_failed
    assert plan.verified is False
    assert "failed on test case" in result.notes


@pytest.mark.asyncio
async def test_verifier_rejects_empty_test_cases(verifier: PlanVerifier):
    plan = build_plan_with_solutions(VALID_REF_CODE, VALID_BF_CODE)
    plan.test_cases = []
    result = await verifier.verify_plan(plan)

    assert result.verified is False
    assert result.status == VerificationStatus.verification_failed
    assert "does not contain any test cases" in result.notes
