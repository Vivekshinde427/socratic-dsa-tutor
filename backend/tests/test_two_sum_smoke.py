import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.problem import Problem
from backend.app.db.models.problem_plan import ProblemPlan
from backend.app.schemas.problem import ProblemCreate
from backend.app.schemas.tutoring_plan import (
    Approach,
    Approaches,
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
from backend.app.services.problem_service import create_problem
from backend.app.services.verifier import PlanVerifier


@pytest.mark.asyncio
async def test_two_sum_smoke_pipeline(db_session: AsyncSession):
    """
    Milestone 1 Core Smoke Test:
    Demonstrates:
    1. Problem persisted in DB (team's own words).
    2. Plan schema validation against typed Pydantic contract.
    3. Brute-force and reference solution sandbox execution against tests.
    4. Verified flag becomes True for a known-good plan.
    5. Deliberately wrong reference behavior is rejected and marked verification_failed.
    """
    # -------------------------------------------------------------------------
    # 1. Problem persisted in DB in our own words
    # -------------------------------------------------------------------------
    problem_in = ProblemCreate(
        title="Target Sum Pair Discovery",
        statement=(
            "Given a sequence of integers 'values' and an integer 'target_sum', "
            "identify the zero-based indices of two distinct elements whose sum "
            "equals 'target_sum'. You may assume each input contains exactly one "
            "valid pair."
        ),
        difficulty=Difficulty.easy,
        topics=["Array", "Hash Table", "Two Pointers"],
        constraints=[
            "2 <= len(values) <= 10^4",
            "-10^9 <= values[i] <= 10^9",
            "-2 * 10^9 <= target_sum <= 2 * 10^9",
        ],
        examples=[
            Example(
                input="[2, 7, 11, 15], 9",
                output="[0, 1]",
                explanation="values[0] + values[1] = 2 + 7 = 9",
            ),
            Example(
                input="[3, 2, 4], 6",
                output="[1, 2]",
                explanation="values[1] + values[2] = 2 + 4 = 6",
            ),
        ],
        source="team_seed",
    )
    persisted_problem = await create_problem(db_session, problem_in)
    assert persisted_problem.id is not None
    assert persisted_problem.slug == "target-sum-pair-discovery"

    # Query back from DB to verify persistence
    stmt = select(Problem).where(Problem.id == persisted_problem.id)
    res = await db_session.execute(stmt)
    loaded_problem = res.scalar_one()
    assert loaded_problem.title == "Target Sum Pair Discovery"

    # -------------------------------------------------------------------------
    # 2. Plan schema validation
    # -------------------------------------------------------------------------
    socratic_step_1 = Step(
        id="step_understand_goal",
        stage=SocraticStage.understand,
        question="What is the objective of the problem regarding returned values?",
        options=[
            MCQOption(id="A", text="Return the actual values that sum to the target"),
            MCQOption(id="B", text="Return the zero-based indices of the two elements"),
            MCQOption(id="C", text="Return boolean true or false if a pair exists"),
            MCQOption(id="D", text="Return the count of all matching pairs"),
        ],
        correct_option_id="B",
        option_feedback=[
            OptionFeedback(option_id="A", why_wrong="The problem specifically asks for the indices, not the values."),
            OptionFeedback(option_id="C", why_wrong="We need the specific pair positions, not merely existence."),
            OptionFeedback(option_id="D", why_wrong="There is guaranteed to be exactly one pair and we need its indices."),
        ],
        hint_ladder=[
            Hint(level=0, content="Look at the return type in the specification."),
            Hint(level=1, content="Notice that example output is [0, 1] rather than [2, 7]."),
        ],
        success_criteria=["Student identifies that indices must be returned."],
    )

    socratic_step_2 = Step(
        id="step_bottleneck",
        stage=SocraticStage.bottleneck,
        question="In the nested-loops brute force approach, what is the main performance bottleneck?",
        options=[
            MCQOption(id="A", text="Repeatedly checking each element's complement in O(n) linear scans"),
            MCQOption(id="B", text="Too much memory allocated for the call stack"),
            MCQOption(id="C", text="Sorting overhead of the initial array"),
            MCQOption(id="D", text="Integer overflow in python addition"),
        ],
        correct_option_id="A",
        option_feedback=[
            OptionFeedback(option_id="B", why_wrong="The brute force uses iteration, not deep recursion."),
            OptionFeedback(option_id="C", why_wrong="The brute force does not sort."),
            OptionFeedback(option_id="D", why_wrong="Python integers handle arbitrary precision; this is an algorithmic complexity issue."),
        ],
        hint_ladder=[
            Hint(level=0, content="Consider why two nested loops take O(n^2) time."),
            Hint(level=1, content="For each number x, how long does it take to check if (target - x) exists in the rest of the array?"),
            Hint(level=2, content="Think about data structures that allow instant lookup by key."),
        ],
        success_criteria=["Student recognizes the linear lookup inside the outer loop as the bottleneck."],
    )

    known_good_plan = TutoringPlan(
        plan_version="1.0.0",
        problem=ProblemSpec(
            title=loaded_problem.title,
            statement=loaded_problem.statement,
            constraints=loaded_problem.constraints,
            examples=[Example(**e) for e in loaded_problem.examples],
            difficulty=Difficulty.easy,
            topics=loaded_problem.topics,
        ),
        pattern="Hash Map / Complement Lookup",
        prerequisites=["Array indexing", "Hash map / dictionary operations"],
        approaches=Approaches(
            brute_force=Approach(
                idea="Inspect all pairs (i, j) with i < j and check if values[i] + values[j] == target_sum.",
                time_complexity="O(n^2)",
                space_complexity="O(1)",
                why_it_works="Guarantees testing every possible pair combination.",
            ),
            optimal=Approach(
                idea="Iterate through values while maintaining a dictionary mapping seen values to their index. For current value v, query if (target_sum - v) exists in the dictionary.",
                time_complexity="O(n)",
                space_complexity="O(n)",
                why_it_works="Reduces complement lookup from O(n) to O(1) average time.",
            ),
        ),
        reference_solution=SolutionCode(
            language="python",
            code="""
def solve(values, target_sum):
    seen = {}
    for i, v in enumerate(values):
        comp = target_sum - v
        if comp in seen:
            return [seen[comp], i]
        seen[v] = i
    return []
""",
        ),
        brute_force_solution=SolutionCode(
            language="python",
            code="""
def solve(values, target_sum):
    n = len(values)
    for i in range(n):
        for j in range(i + 1, n):
            if values[i] + values[j] == target_sum:
                return [i, j]
    return []
""",
        ),
        test_cases=[
            TestCase(
                input="[2, 7, 11, 15], 9",
                expected_output="[0, 1]",
                category=TestCaseCategory.sample,
            ),
            TestCase(
                input="[3, 2, 4], 6",
                expected_output="[1, 2]",
                category=TestCaseCategory.sample,
            ),
            TestCase(
                input="[3, 3], 6",
                expected_output="[0, 1]",
                category=TestCaseCategory.edge,
            ),
            TestCase(
                input="[-1, -2, -3, -4, -5], -8",
                expected_output="[2, 4]",
                category=TestCaseCategory.edge,
            ),
        ],
        socratic_steps=[socratic_step_1, socratic_step_2],
        misconceptions=[],
        confidence=1.0,
        verified=False,
        verification_status=VerificationStatus.unverified,
        model_name="gemini-2.5-flash",
        prompt_version="1.0.0",
    )

    # -------------------------------------------------------------------------
    # 3 & 4. Sandbox verification: verified flag becomes True for known-good plan
    # -------------------------------------------------------------------------
    verifier = PlanVerifier()
    verification_good = await verifier.verify_plan(known_good_plan)

    assert verification_good.verified is True
    assert verification_good.status == VerificationStatus.verified
    assert known_good_plan.verified is True
    assert known_good_plan.verification_status == VerificationStatus.verified
    assert len(verification_good.test_results) == 4
    for t_res in verification_good.test_results:
        assert t_res.passed is True

    # Persist verified plan in DB
    good_plan_record = ProblemPlan(
        problem_id=loaded_problem.id,
        plan_version=known_good_plan.plan_version,
        raw_plan=known_good_plan.model_dump(),
        verified=known_good_plan.verified,
        verification_status=known_good_plan.verification_status.value,
        verification_notes=known_good_plan.verification_notes,
        model_name=known_good_plan.model_name,
        prompt_version=known_good_plan.prompt_version,
    )
    db_session.add(good_plan_record)
    await db_session.commit()
    await db_session.refresh(good_plan_record)
    assert good_plan_record.verified is True
    assert good_plan_record.verification_status == "verified"

    # -------------------------------------------------------------------------
    # 5. Deliberately wrong reference behavior is rejected and marked verification_failed
    # -------------------------------------------------------------------------
    broken_plan = known_good_plan.model_copy(deep=True)
    broken_plan.verified = False
    broken_plan.verification_status = VerificationStatus.unverified
    # Reference returns constant bogus indices
    broken_plan.reference_solution.code = """
def solve(values, target_sum):
    return [999, 999]
"""
    verification_broken = await verifier.verify_plan(broken_plan)

    assert verification_broken.verified is False
    assert verification_broken.status == VerificationStatus.verification_failed
    assert broken_plan.verified is False
    assert broken_plan.verification_status == VerificationStatus.verification_failed
    assert "Output mismatch" in verification_broken.notes

    # Persist broken plan in DB to demonstrate explicit failure tracking
    broken_plan_record = ProblemPlan(
        problem_id=loaded_problem.id,
        plan_version=broken_plan.plan_version,
        raw_plan=broken_plan.model_dump(),
        verified=broken_plan.verified,
        verification_status=broken_plan.verification_status.value,
        verification_notes=broken_plan.verification_notes,
        model_name=broken_plan.model_name,
        prompt_version=broken_plan.prompt_version,
    )
    db_session.add(broken_plan_record)
    await db_session.commit()
    await db_session.refresh(broken_plan_record)
    assert broken_plan_record.verified is False
    assert broken_plan_record.verification_status == "verification_failed"
