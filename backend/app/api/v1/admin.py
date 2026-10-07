from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.deps import get_db, require_admin
from backend.app.db.models.problem_plan import ProblemPlan
from backend.app.db.models.system_log import SystemLog
from backend.app.db.models.user import User
from backend.app.schemas.problem import PlanVerificationResponse
from backend.app.services.plan_generator import plan_generation_service
from backend.app.services.problem_service import get_problem_by_id
from backend.app.services.verifier import plan_verifier

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post(
    "/problems/{problem_id}/regenerate-plan",
    response_model=PlanVerificationResponse,
)
async def regenerate_problem_plan(
    problem_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    problem = await get_problem_by_id(db, problem_id)
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found",
        )

    # 1. Generate plan using Problem Analyst
    plan = await plan_generation_service.generate_plan(problem)

    # 2. Verify plan using isolated sandbox
    verification = await plan_verifier.verify_plan(plan)

    # 3. Persist plan in DB
    problem_plan = ProblemPlan(
        problem_id=problem.id,
        plan_version=plan.plan_version,
        raw_plan=plan.model_dump(),
        verified=verification.verified,
        verification_status=verification.status.value,
        verification_notes=verification.notes,
        model_name=plan.model_name,
        prompt_version=plan.prompt_version,
    )
    db.add(problem_plan)

    # 4. Log event in system_logs
    log_entry = SystemLog(
        event_type="plan_generation_and_verification",
        user_id=admin.id,
        problem_id=problem.id,
        payload={
            "verified": verification.verified,
            "status": verification.status.value,
            "model_name": plan.model_name,
            "prompt_version": plan.prompt_version,
            "notes": verification.notes,
        },
    )
    db.add(log_entry)

    await db.commit()

    return PlanVerificationResponse(
        problem_id=problem.id,
        verified=verification.verified,
        verification_status=verification.status,
        notes=verification.notes,
    )


@router.get("/logs")
async def get_system_logs(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    stmt = (
        select(SystemLog)
        .order_by(SystemLog.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "event_type": log.event_type,
            "user_id": log.user_id,
            "problem_id": log.problem_id,
            "payload": log.payload,
            "created_at": log.created_at,
        }
        for log in logs
    ]
