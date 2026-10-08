"""
Learning Progress and Mastery Endpoints (Milestone 2, SPEC §15).
"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.deps import get_current_user, get_db
from backend.app.db.models.learning_progress import LearningProgress
from backend.app.db.models.problem import Problem
from backend.app.db.models.user import User
from backend.app.schemas.session import LearningProgressOut
from backend.app.services.mastery_service import mastery_service

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("/me", response_model=List[LearningProgressOut])
async def get_my_progress(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get learning progress and mastery values for all attempted DSA topics."""
    return await mastery_service.get_user_progress(db=db, user_id=user.id)


@router.get("/recommendations")
async def get_recommendations(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Get recommended problems/topics based on student mastery gaps.
    Prioritizes topics where mastery is lowest (< 0.5).
    """
    progress = await mastery_service.get_user_progress(db=db, user_id=user.id)
    # Find weak topics
    weak_topics = [p.topic for p in progress if p.mastery < 0.6]

    # Query problems matching weak topics or easy problems
    query = select(Problem).limit(5)
    res = await db.execute(query)
    problems = res.scalars().all()

    recommendations = [
        {
            "problem_id": prob.id,
            "title": prob.title,
            "difficulty": prob.difficulty,
            "topics": prob.topics,
            "reason": (
                f"Recommended to strengthen mastery in {', '.join(prob.topics)}"
                if any(t in weak_topics for t in prob.topics)
                else "Recommended foundation problem"
            ),
        }
        for prob in problems
    ]

    return {
        "weak_topics": weak_topics,
        "recommendations": recommendations,
    }
