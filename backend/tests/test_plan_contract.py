import pytest
from pydantic import ValidationError

from backend.app.schemas.tutoring_plan import (
    Approach,
    Approaches,
    ClientStepDTO,
    Difficulty,
    Example,
    Hint,
    MCQOption,
    OptionFeedback,
    ProblemSpec,
    SocraticStage,
    SolutionCode,
    Step,
    TestCase,
    TestCaseCategory,
    TutoringPlan,
    VerificationStatus,
)


def make_valid_step() -> Step:
    return Step(
        id="step_1",
        stage=SocraticStage.understand,
        question="What are we given and what are we looking for?",
        options=[
            MCQOption(id="A", text="An array of integers and a target sum"),
            MCQOption(id="B", text="A binary search tree and a node key"),
        ],
        correct_option_id="A",
        option_feedback=[
            OptionFeedback(option_id="B", why_wrong="The problem is on arrays, not trees."),
        ],
        hint_ladder=[
            Hint(level=0, content="Re-read the problem input definitions."),
            Hint(level=1, content="Look at the types: nums: List[int], target: int"),
        ],
        success_criteria=["Student understands input is an integer array"],
    )


def make_valid_plan() -> TutoringPlan:
    step = make_valid_step()
    return TutoringPlan(
        plan_version="1.0.0",
        problem=ProblemSpec(
            title="Pair Sum Problem",
            statement="Given an array of integers and a target integer, return the indices of two numbers that add up to target.",
            constraints=["2 <= len(nums) <= 10^4", "-10^9 <= nums[i] <= 10^9"],
            examples=[
                Example(input="[2, 7, 11, 15], 9", output="[0, 1]", explanation="nums[0] + nums[1] == 9")
            ],
            difficulty=Difficulty.easy,
            topics=["Array", "Hash Table"],
        ),
        pattern="Hash Map Complement Lookup",
        prerequisites=["Basic arrays", "Hash maps"],
        approaches=Approaches(
            brute_force=Approach(
                idea="Check every pair of elements with two nested loops.",
                time_complexity="O(n^2)",
                space_complexity="O(1)",
                why_it_works="Exhaustively tries every pair.",
            ),
            optimal=Approach(
                idea="Store seen numbers and their indices in a hash map.",
                time_complexity="O(n)",
                space_complexity="O(n)",
                why_it_works="Allows O(1) complement lookup for each element.",
            ),
        ),
        reference_solution=SolutionCode(
            language="python",
            code="def solve(nums, target):\n    seen = {}\n    for i, num in enumerate(nums):\n        comp = target - num\n        if comp in seen:\n            return [seen[comp], i]\n        seen[num] = i\n    return []\n",
        ),
        brute_force_solution=SolutionCode(
            language="python",
            code="def solve(nums, target):\n    for i in range(len(nums)):\n        for j in range(i + 1, len(nums)):\n            if nums[i] + nums[j] == target:\n                return [i, j]\n    return []\n",
        ),
        test_cases=[
            TestCase(input="[2, 7, 11, 15], 9", expected_output="[0, 1]", category=TestCaseCategory.sample),
            TestCase(input="[3, 2, 4], 6", expected_output="[1, 2]", category=TestCaseCategory.sample),
            TestCase(input="[3, 3], 6", expected_output="[0, 1]", category=TestCaseCategory.edge),
        ],
        socratic_steps=[step],
        misconceptions=[],
        confidence=1.0,
        verified=False,
        verification_status=VerificationStatus.unverified,
        model_name="gemini-2.5-flash",
        prompt_version="1.0.0",
    )


def test_valid_plan_schema():
    plan = make_valid_plan()
    assert plan.plan_version == "1.0.0"
    assert plan.problem.title == "Pair Sum Problem"
    assert len(plan.socratic_steps) == 1
    assert plan.verification_status == VerificationStatus.unverified


def test_step_invalid_correct_option_id():
    with pytest.raises(ValidationError) as exc_info:
        Step(
            id="step_bad",
            stage=SocraticStage.understand,
            question="Question?",
            options=[
                MCQOption(id="A", text="Option A"),
                MCQOption(id="B", text="Option B"),
            ],
            correct_option_id="C",  # Not in options!
        )
    assert "correct_option_id 'C' must be one of the option IDs" in str(exc_info.value)


def test_step_too_few_options():
    with pytest.raises(ValidationError) as exc_info:
        Step(
            id="step_bad",
            stage=SocraticStage.understand,
            question="Question?",
            options=[MCQOption(id="A", text="Only one option")],
            correct_option_id="A",
        )
    assert "at least 2 options" in str(exc_info.value)


def test_client_step_dto_leak_prevention():
    step = make_valid_step()
    client_dto = ClientStepDTO.from_step(step)

    # Convert to dict as would be serialized in JSON response
    dto_dict = client_dto.model_dump()

    # Client DTO must NEVER contain server secrets
    assert "correct_option_id" not in dto_dict
    assert "option_feedback" not in dto_dict
    assert "hint_ladder" not in dto_dict  # Hints are served progressively upon request, not all at once!

    # Check safe fields exist
    assert dto_dict["id"] == "step_1"
    assert dto_dict["question"] == step.question
    assert len(dto_dict["options"]) == 2
    for opt in dto_dict["options"]:
        assert "id" in opt
        assert "text" in opt
        assert "is_correct" not in opt
