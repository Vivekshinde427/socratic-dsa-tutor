from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient

from backend.app.db.models.user import User
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
    TutoringPlan,
    VerificationStatus,
)


def create_mock_tutoring_plan(title: str = "Test Problem") -> TutoringPlan:
    return TutoringPlan(
        plan_version="1.0.0",
        problem=ProblemSpec(
            title=title,
            statement="Find two numbers.",
            constraints=[],
            examples=[Example(input="[1, 2], 3", output="[0, 1]")],
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
                why_it_works="O(1) lookup",
            ),
        ),
        reference_solution=SolutionCode(
            language="python",
            code="def solve(nums, target):\n    for i in range(len(nums)):\n        for j in range(i+1, len(nums)):\n            if nums[i]+nums[j]==target: return [i, j]\n    return []\n",
        ),
        brute_force_solution=SolutionCode(
            language="python",
            code="def solve(nums, target):\n    for i in range(len(nums)):\n        for j in range(i+1, len(nums)):\n            if nums[i]+nums[j]==target: return [i, j]\n    return []\n",
        ),
        test_cases=[
            TestCase(input="[1, 2], 3", expected_output="[0, 1]"),
        ],
        socratic_steps=[
            Step(
                id="s1",
                stage=SocraticStage.understand,
                question="What are we solving?",
                options=[
                    MCQOption(id="A", text="Finding pair"),
                    MCQOption(id="B", text="Finding triplet"),
                ],
                correct_option_id="A",
            )
        ],
        misconceptions=[],
        confidence=1.0,
        verified=False,
        verification_status=VerificationStatus.unverified,
        model_name="mock-gemini",
        prompt_version="1.0.0",
    )


@pytest.mark.asyncio
async def test_paste_and_get_problem(
    client: AsyncClient, student_user: User, student_auth_headers: dict
):
    paste_data = {
        "title": "Target Sum Indices",
        "statement": "Given an array of integers, return the indices of two elements summing to a target value.",
    }
    resp = await client.post(
        "/api/v1/problems/paste", json=paste_data, headers=student_auth_headers
    )
    assert resp.status_code == 201
    prob = resp.json()
    assert prob["title"] == "Target Sum Indices"
    assert prob["slug"] == "target-sum-indices"
    assert prob["has_plan"] is False

    # Get problem details
    prob_id = prob["id"]
    get_resp = await client.get(f"/api/v1/problems/{prob_id}")
    assert get_resp.status_code == 200
    details = get_resp.json()
    assert details["title"] == "Target Sum Indices"
    assert details["statement"] == paste_data["statement"]


@pytest.mark.asyncio
async def test_admin_regenerate_plan_and_logs(
    client: AsyncClient,
    admin_user: User,
    admin_auth_headers: dict,
    student_auth_headers: dict,
):
    # 1. First paste a problem
    paste_resp = await client.post(
        "/api/v1/problems/paste",
        json={"title": "Sum Problem", "statement": "Given nums, find sum."},
        headers=admin_auth_headers,
    )
    prob_id = paste_resp.json()["id"]

    # 2. Student trying admin endpoint -> 403 Forbidden
    student_admin_resp = await client.post(
        f"/api/v1/admin/problems/{prob_id}/regenerate-plan",
        headers=student_auth_headers,
    )
    assert student_admin_resp.status_code == 403

    # 3. Admin regenerates plan with mock LLM
    mock_plan = create_mock_tutoring_plan("Sum Problem")
    with patch(
        "backend.app.services.plan_generator.plan_generation_service.generate_plan",
        new=AsyncMock(return_value=mock_plan),
    ):
        admin_resp = await client.post(
            f"/api/v1/admin/problems/{prob_id}/regenerate-plan",
            headers=admin_auth_headers,
        )
        assert admin_resp.status_code == 200
        plan_res = admin_resp.json()
        assert plan_res["verified"] is True
        assert plan_res["verification_status"] == "verified"

    # 4. Check admin logs
    logs_resp = await client.get("/api/v1/admin/logs", headers=admin_auth_headers)
    assert logs_resp.status_code == 200
    logs = logs_resp.json()
    assert len(logs) > 0
    assert logs[0]["event_type"] == "plan_generation_and_verification"
