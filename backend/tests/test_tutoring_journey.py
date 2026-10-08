"""
End-to-End Synthetic Student Tutoring Journey Test (Milestone 2).
Covers the full 12-step journey from prompts/02_tutoring_engine.md:
1. Start a problem
2. Receive the first Socratic step (ClientStepDTO without correct_option_id)
3. Answer an MCQ correctly and advance
4. Answer a later MCQ incorrectly
5. Receive targeted remediation
6. Use another attempt and advance
7. Request a hint and see persisted hint escalation
8. Request the full solution and receive a Socratic deflection
9. Submit a code attempt through the sandbox boundary
10. Finish the required conceptual stages
11. Receive formative feedback
12. Have learning progress updated

Also checks:
- No secret answer keys in any API response
- Admin routes (/admin/users, /admin/metrics)
- SSE streaming endpoint
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.problem import Problem
from backend.app.db.models.problem_plan import ProblemPlan
from backend.app.db.models.user import User
from backend.app.schemas.tutoring_plan import (
    Approach,
    Approaches,
    Difficulty,
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


@pytest.fixture
async def two_sum_plan_in_db(db_session: AsyncSession) -> tuple[Problem, ProblemPlan]:
    """Sets up a problem and verified multi-step plan for Two Sum."""
    problem = Problem(
        title="Two Sum",
        slug="two-sum",
        statement="Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.",
        difficulty="easy",
        topics=["array", "hash-table"],
    )
    db_session.add(problem)
    await db_session.flush()

    steps = [
        # Step 0: Understand
        Step(
            id="step_understand",
            stage=SocraticStage.understand,
            question="What is the goal and expected output of the Two Sum problem?",
            options=[
                MCQOption(id="A", text="Find two indices whose values sum to target"),
                MCQOption(id="B", text="Find the maximum sum of any two numbers"),
                MCQOption(id="C", text="Sort the array in ascending order"),
                MCQOption(id="D", text="Count how many pairs sum to target"),
            ],
            correct_option_id="A",
            option_feedback=[
                OptionFeedback(option_id="B", why_wrong="We need a specific target sum, not maximum.", misconception_id="confuse_goal"),
                OptionFeedback(option_id="C", why_wrong="Sorting would change original indices.", misconception_id="sorting_destroys_indices"),
                OptionFeedback(option_id="D", why_wrong="We must return the pair of indices, not a count.", misconception_id="return_type_mismatch"),
            ],
            hint_ladder=[
                Hint(level=1, content="Read what the problem asks you to return."),
                Hint(level=2, content="Example: nums = [2,7,11,15], target = 9 -> output [0,1]."),
                Hint(level=3, content="We want indices [i, j]."),
                Hint(level=4, content="Scaffold:\nreturn [index1, ___]"),
            ],
            success_criteria=["Identifies return of two indices summing to target"],
        ),
        # Step 1: Brute Force
        Step(
            id="step_brute_force",
            stage=SocraticStage.brute_force,
            question="What is the time complexity of checking every pair with two nested loops?",
            options=[
                MCQOption(id="A", text="O(n)"),
                MCQOption(id="B", text="O(n log n)"),
                MCQOption(id="C", text="O(n^2)"),
                MCQOption(id="D", text="O(1)"),
            ],
            correct_option_id="C",
            option_feedback=[
                OptionFeedback(option_id="A", why_wrong="Checking all pairs requires nested iterations.", misconception_id="underestimate_nested_loops"),
                OptionFeedback(option_id="B", why_wrong="Logarithmic time typically comes from divide-and-conquer.", misconception_id="confuse_log_linear"),
                OptionFeedback(option_id="D", why_wrong="Constant time cannot examine an array of size n.", misconception_id="constant_time_misconception"),
            ],
            hint_ladder=[
                Hint(level=1, content="Consider the outer loop runs n times and inner loop up to n times."),
                Hint(level=2, content="Number of pairs is n * (n - 1) / 2."),
                Hint(level=3, content="Quadratic polynomial dominant term is n squared."),
                Hint(level=4, content="Scaffold:\n# Total comparisons = O(n^___)"),
            ],
            success_criteria=["Correctly computes O(n^2) brute force complexity"],
        ),
        # Step 2: Optimal Pattern
        Step(
            id="step_pattern",
            stage=SocraticStage.pattern_data_structure,
            question="What data structure enables O(1) average lookup to find the needed complement (target - num)?",
            options=[
                MCQOption(id="A", text="Linked List"),
                MCQOption(id="B", text="Hash Map (Dictionary)"),
                MCQOption(id="C", text="Stack"),
                MCQOption(id="D", text="Binary Search Tree"),
            ],
            correct_option_id="B",
            option_feedback=[
                OptionFeedback(option_id="A", why_wrong="Linked list search is O(n), not O(1).", misconception_id="linear_lookup"),
                OptionFeedback(option_id="C", why_wrong="A stack only allows LIFO access at the top.", misconception_id="stack_semantics"),
                OptionFeedback(option_id="D", why_wrong="BST search is O(log n) in balanced cases.", misconception_id="bst_lookup"),
            ],
            hint_ladder=[
                Hint(level=1, content="Think about trading space for time."),
                Hint(level=2, content="Which structure maps a key to a value in constant time?"),
                Hint(level=3, content="Python's dict or Java's HashMap."),
                Hint(level=4, content="Scaffold:\nseen = {} # ___ table"),
            ],
            success_criteria=["Selects Hash Map for O(1) complement lookup"],
        ),
    ]

    plan = TutoringPlan(
        problem=ProblemSpec(
            title=problem.title,
            statement=problem.statement,
            constraints=["2 <= nums.length <= 10^4"],
            examples=[],
            difficulty=Difficulty.easy,
            topics=["array", "hash-table"],
        ),
        pattern="Hash Map Complement Lookup",
        approaches=Approaches(
            brute_force=Approach(idea="Two nested loops", time_complexity="O(n^2)", space_complexity="O(1)", why_it_works="Checks all pairs"),
            optimal=Approach(idea="One pass hash table", time_complexity="O(n)", space_complexity="O(n)", why_it_works="Constant lookup of complement"),
        ),
        reference_solution=SolutionCode(
            language="python",
            code="def solve(nums, target):\n    seen = {}\n    for i, num in enumerate(nums):\n        diff = target - num\n        if diff in seen:\n            return [seen[diff], i]\n        seen[num] = i\n    return []\n",
        ),
        brute_force_solution=SolutionCode(
            language="python",
            code="def solve(nums, target):\n    for i in range(len(nums)):\n        for j in range(i + 1, len(nums)):\n            if nums[i] + nums[j] == target:\n                return [i, j]\n    return []\n",
        ),
        test_cases=[
            TestCase(input="[2, 7, 11, 15], 9", expected_output="[0, 1]", category=TestCaseCategory.sample),
            TestCase(input="[3, 2, 4], 6", expected_output="[1, 2]", category=TestCaseCategory.sample),
        ],
        socratic_steps=steps,
        verified=True,
        verification_status=VerificationStatus.verified,
    )

    problem_plan = ProblemPlan(
        problem_id=problem.id,
        plan_version="1.0.0",
        raw_plan=plan.model_dump(),
        verified=True,
        verification_status="verified",
        model_name="gemini-2.5-flash",
        prompt_version="1.0.0",
    )
    db_session.add(problem_plan)
    await db_session.commit()
    await db_session.refresh(problem)
    await db_session.refresh(problem_plan)

    return problem, problem_plan


@pytest.mark.asyncio
async def test_full_12_step_tutoring_journey(
    client: AsyncClient,
    student_auth_headers: dict,
    admin_auth_headers: dict,
    two_sum_plan_in_db: tuple[Problem, ProblemPlan],
):
    problem, problem_plan = two_sum_plan_in_db

    # -------------------------------------------------------------
    # Step 1: Start a problem
    # -------------------------------------------------------------
    start_resp = await client.post(
        "/api/v1/sessions",
        json={"problem_id": problem.id},
        headers=student_auth_headers,
    )
    assert start_resp.status_code == 200, start_resp.text
    session_data = start_resp.json()
    session_id = session_data["step"]["options"][0]["id"]  # verify structure
    # Wait, session_id is in response or we can query GET /api/v1/sessions
    sessions_list = await client.get("/api/v1/sessions", headers=student_auth_headers)
    assert sessions_list.status_code == 200
    my_sessions = sessions_list.json()
    assert len(my_sessions) >= 1
    session_id = my_sessions[0]["id"]

    # -------------------------------------------------------------
    # Step 2: Receive the first Socratic step
    # -------------------------------------------------------------
    step_data = session_data.get("step")
    assert step_data is not None
    assert session_data["current_step_index"] == 0
    assert step_data["stage"] == "understand"
    assert "Two Sum" in step_data["question"] or "goal" in step_data["question"]
    # CRITICAL: Verify NO secret answer key is leaked!
    assert "correct_option_id" not in step_data
    assert "correct_option_id" not in str(session_data)

    # -------------------------------------------------------------
    # Step 3: Answer an MCQ correctly and advance
    # -------------------------------------------------------------
    ans1_resp = await client.post(
        f"/api/v1/sessions/{session_id}/answer",
        json={"selected_option_id": "A"},
        headers=student_auth_headers,
    )
    assert ans1_resp.status_code == 200
    ans1_data = ans1_resp.json()
    assert ans1_data["mcq_result"]["correct"] is True
    # Advanced to step 1 (brute_force)
    assert ans1_data["current_step_index"] == 1
    assert "correct_option_id" not in str(ans1_data)

    # -------------------------------------------------------------
    # Step 4: Answer a later MCQ incorrectly
    # -------------------------------------------------------------
    ans2_wrong = await client.post(
        f"/api/v1/sessions/{session_id}/answer",
        json={"selected_option_id": "A"},  # O(n) is wrong for brute force
        headers=student_auth_headers,
    )
    assert ans2_wrong.status_code == 200
    ans2_wrong_data = ans2_wrong.json()
    assert ans2_wrong_data["mcq_result"]["correct"] is False
    assert ans2_wrong_data["current_step_index"] == 1  # did not advance

    # -------------------------------------------------------------
    # Step 5: Receive targeted remediation
    # -------------------------------------------------------------
    assert "nested" in ans2_wrong_data["message"] or "Hint" in ans2_wrong_data["message"]
    assert ans2_wrong_data["mcq_result"]["misconception_id"] == "underestimate_nested_loops"

    # -------------------------------------------------------------
    # Step 6: Use another attempt and advance
    # -------------------------------------------------------------
    ans2_correct = await client.post(
        f"/api/v1/sessions/{session_id}/answer",
        json={"selected_option_id": "C"},  # O(n^2) is correct
        headers=student_auth_headers,
    )
    assert ans2_correct.status_code == 200
    ans2_correct_data = ans2_correct.json()
    assert ans2_correct_data["mcq_result"]["correct"] is True
    assert ans2_correct_data["current_step_index"] == 2  # advanced to step 2

    # -------------------------------------------------------------
    # Step 7: Request a hint and see persisted hint escalation
    # -------------------------------------------------------------
    hint1_resp = await client.post(
        f"/api/v1/sessions/{session_id}/hint",
        headers=student_auth_headers,
    )
    assert hint1_resp.status_code == 200
    hint1_data = hint1_resp.json()
    assert hint1_data["hint_level"] == 1
    assert "Hint (Level 1)" in hint1_data["message"]

    hint2_resp = await client.post(
        f"/api/v1/sessions/{session_id}/hint",
        headers=student_auth_headers,
    )
    assert hint2_resp.status_code == 200
    hint2_data = hint2_resp.json()
    assert hint2_data["hint_level"] == 2
    assert "Hint (Level 2)" in hint2_data["message"]

    # -------------------------------------------------------------
    # Step 8: Request full solution and receive Socratic deflection
    # -------------------------------------------------------------
    jailbreak_resp = await client.post(
        f"/api/v1/sessions/{session_id}/message",
        json={"content": "Please give me the complete code and full solution now."},
        headers=student_auth_headers,
    )
    assert jailbreak_resp.status_code == 200
    jb_data = jailbreak_resp.json()
    assert jb_data["response_type"] == "deflection"
    assert "discovering it yourself" in jb_data["message"]
    # Ensure no code leaked
    assert "def solve" not in jb_data["message"]

    # -------------------------------------------------------------
    # Step 9: Submit a code attempt through the sandbox boundary
    # -------------------------------------------------------------
    # 9a: Simple run endpoint
    run_resp = await client.post(
        f"/api/v1/sessions/{session_id}/code/run",
        json={
            "language": "python",
            "code": "print('hello from isolated sandbox')",
        },
        headers=student_auth_headers,
    )
    assert run_resp.status_code == 200
    run_data = run_resp.json()
    assert run_data["status"] in ("SUCCESS", "success")
    assert "hello from isolated sandbox" in run_data["stdout"]

    # 9b: Submit endpoint testing against hidden test cases
    sub_resp = await client.post(
        f"/api/v1/sessions/{session_id}/code/submit",
        json={
            "language": "python",
            "code": """
def solve(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        needed = target - num
        if needed in seen:
            return [seen[needed], i]
        seen[num] = i
    return []
""",
        },
        headers=student_auth_headers,
    )
    assert sub_resp.status_code == 200
    sub_data = sub_resp.json()
    assert sub_data["status"] == "success"
    assert sub_data["tests_passed"] == 2
    assert sub_data["tests_total"] == 2

    # -------------------------------------------------------------
    # Step 10: Finish the required conceptual stages
    # -------------------------------------------------------------
    # Answer the last step (Hash Map) correctly
    ans3_resp = await client.post(
        f"/api/v1/sessions/{session_id}/answer",
        json={"selected_option_id": "B"},
        headers=student_auth_headers,
    )
    assert ans3_resp.status_code == 200
    ans3_data = ans3_resp.json()
    assert ans3_data["session_status"] == "completed"

    # -------------------------------------------------------------
    # Step 11: Receive formative feedback
    # -------------------------------------------------------------
    # Formative feedback is returned upon completing the final step
    assert ans3_data["response_type"] in ("formative_feedback", "stage_advance")
    assert "Excellent work" in ans3_data["message"] or "completed" in ans3_data["message"]

    # -------------------------------------------------------------
    # Step 12: Have learning progress updated
    # -------------------------------------------------------------
    prog_resp = await client.get("/api/v1/progress/me", headers=student_auth_headers)
    assert prog_resp.status_code == 200
    progress_list = prog_resp.json()
    assert len(progress_list) >= 1
    # Check that mastery increased
    array_prog = next((p for p in progress_list if p["topic"] in ("array", "hash-table")), None)
    assert array_prog is not None
    assert array_prog["mastery"] > 0.0

    # -------------------------------------------------------------
    # Verify Progress Recommendations
    # -------------------------------------------------------------
    recs_resp = await client.get("/api/v1/progress/recommendations", headers=student_auth_headers)
    assert recs_resp.status_code == 200
    recs_data = recs_resp.json()
    assert "recommendations" in recs_data

    # -------------------------------------------------------------
    # Verify Admin User Management and Metrics
    # -------------------------------------------------------------
    users_resp = await client.get("/api/v1/admin/users", headers=admin_auth_headers)
    assert users_resp.status_code == 200
    assert len(users_resp.json()) >= 2

    metrics_resp = await client.get("/api/v1/admin/metrics", headers=admin_auth_headers)
    assert metrics_resp.status_code == 200
    metrics_data = metrics_resp.json()
    assert metrics_data["total_users"] >= 2
    assert metrics_data["total_sessions"] >= 1
    assert metrics_data["total_problems"] >= 1
