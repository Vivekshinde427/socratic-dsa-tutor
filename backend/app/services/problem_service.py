import re
import uuid
from typing import List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from backend.app.db.models.problem import Problem
from backend.app.db.models.problem_plan import ProblemPlan
from backend.app.schemas.problem import ProblemCreate, ProblemPasteRequest
from backend.app.schemas.tutoring_plan import Difficulty, Example


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text or "problem"


async def get_problem_by_id(
    db: AsyncSession, problem_id: str
) -> Optional[Problem]:
    stmt = (
        select(Problem)
        .options(selectinload(Problem.plans))
        .where(Problem.id == problem_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_problems(
    db: AsyncSession, skip: int = 0, limit: int = 50
) -> List[Problem]:
    stmt = (
        select(Problem)
        .options(selectinload(Problem.plans))
        .offset(skip)
        .limit(limit)
        .order_by(Problem.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_problem(
    db: AsyncSession, problem_in: ProblemCreate
) -> Problem:
    base_slug = slugify(problem_in.title)
    slug = base_slug
    # Ensure unique slug
    counter = 1
    while True:
        stmt = select(Problem).where(Problem.slug == slug)
        res = await db.execute(stmt)
        if not res.scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    problem = Problem(
        title=problem_in.title,
        slug=slug,
        statement=problem_in.statement,
        difficulty=problem_in.difficulty.value,
        topics=problem_in.topics,
        constraints=problem_in.constraints,
        examples=[ex.model_dump() for ex in problem_in.examples],
        source=problem_in.source,
    )
    db.add(problem)
    await db.commit()
    await db.refresh(problem)
    return problem


async def paste_problem(
    db: AsyncSession, paste_in: ProblemPasteRequest
) -> Problem:
    title = paste_in.title
    if not title:
        first_line = paste_in.statement.strip().split("\n")[0][:60]
        title = first_line or f"Pasted Problem {uuid.uuid4().hex[:6]}"

    problem_in = ProblemCreate(
        title=title,
        statement=paste_in.statement.strip(),
        difficulty=Difficulty.easy,
        topics=["Pasted"],
        constraints=[],
        examples=[],
        source="pasted",
    )
    return await create_problem(db, problem_in)
