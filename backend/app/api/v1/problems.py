from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.deps import get_db, get_current_user
from backend.app.db.models.user import User
from backend.app.schemas.problem import (
    ProblemDetailOut,
    ProblemOut,
    ProblemPasteRequest,
)
from backend.app.schemas.tutoring_plan import (
    ClientPlanOverviewDTO,
    ClientProblemDTO,
    Difficulty,
    Example,
    VerificationStatus,
)
from backend.app.services.problem_service import (
    get_problem_by_id,
    get_problems,
    paste_problem,
)

router = APIRouter(prefix="/problems", tags=["problems"])


@router.get("", response_model=List[ProblemOut])
async def list_problems(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    problems = await get_problems(db, skip=skip, limit=limit)
    return [
        ProblemOut(
            id=p.id,
            title=p.title,
            slug=p.slug,
            difficulty=Difficulty(p.difficulty),
            topics=p.topics,
            source=p.source,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in problems
    ]


@router.get("/{problem_id}", response_model=ProblemDetailOut)
async def get_problem(
    problem_id: str,
    db: AsyncSession = Depends(get_db),
):
    problem = await get_problem_by_id(db, problem_id)
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found",
        )

    has_plan = len(problem.plans) > 0
    latest_plan = problem.plans[-1] if has_plan else None

    return ProblemDetailOut(
        id=problem.id,
        title=problem.title,
        slug=problem.slug,
        difficulty=Difficulty(problem.difficulty),
        topics=problem.topics,
        source=problem.source,
        statement=problem.statement,
        constraints=problem.constraints,
        examples=[Example(**ex) for ex in problem.examples],
        created_at=problem.created_at,
        updated_at=problem.updated_at,
        has_plan=has_plan,
        plan_verified=latest_plan.verified if latest_plan else False,
        verification_status=(
            VerificationStatus(latest_plan.verification_status)
            if latest_plan
            else None
        ),
    )


@router.post("/paste", response_model=ProblemDetailOut, status_code=status.HTTP_201_CREATED)
async def paste_new_problem(
    paste_in: ProblemPasteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    problem = await paste_problem(db, paste_in)
    return ProblemDetailOut(
        id=problem.id,
        title=problem.title,
        slug=problem.slug,
        difficulty=Difficulty(problem.difficulty),
        topics=problem.topics,
        source=problem.source,
        statement=problem.statement,
        constraints=problem.constraints,
        examples=[],
        created_at=problem.created_at,
        updated_at=problem.updated_at,
        has_plan=False,
        plan_verified=False,
        verification_status=None,
    )
