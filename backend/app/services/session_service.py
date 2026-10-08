"""Session management service for tutoring sessions."""
from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import logger
from backend.app.db.models.session import Session
from backend.app.db.models.message import Message
from backend.app.db.models.problem import Problem
from backend.app.db.models.problem_plan import ProblemPlan


async def create_session(
    db: AsyncSession,
    user_id: str,
    problem_id: str,
    plan_id: Optional[str] = None,
) -> Session:
    """Create a new tutoring session."""
    session = Session(
        user_id=user_id,
        problem_id=problem_id,
        plan_id=plan_id,
        current_step_index=0,
        current_hint_level=0,
        current_attempts=0,
        status="active",
        stage_progress={},
        rolling_summary="",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    logger.info(f"Created session {session.id} for user={user_id}, problem={problem_id}")
    return session


async def get_session_by_id(
    db: AsyncSession, session_id: str
) -> Optional[Session]:
    """Get a session by ID with related data."""
    stmt = select(Session).where(Session.id == session_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_sessions(
    db: AsyncSession, user_id: str, limit: int = 50
) -> List[Session]:
    """Get all sessions for a user."""
    stmt = (
        select(Session)
        .where(Session.user_id == user_id)
        .order_by(Session.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_session_messages(
    db: AsyncSession, session_id: str, limit: int = 200
) -> List[Message]:
    """Get messages for a session, ordered by creation time."""
    stmt = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def add_message(
    db: AsyncSession,
    session_id: str,
    role: str,
    content: str,
    message_type: str = "text",
    metadata_json: dict = None,
    step_index: Optional[int] = None,
) -> Message:
    """Add a message to a session conversation."""
    msg = Message(
        session_id=session_id,
        role=role,
        content=content,
        message_type=message_type,
        metadata_json=metadata_json or {},
        step_index=step_index,
    )
    db.add(msg)
    await db.flush()
    return msg


async def get_recent_messages(
    db: AsyncSession, session_id: str, count: int = 8
) -> List[Message]:
    """Get recent N messages for context window (SPEC §11: 6-8 turns)."""
    stmt = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(count)
    )
    result = await db.execute(stmt)
    messages = list(result.scalars().all())
    messages.reverse()  # Return in chronological order
    return messages


async def get_latest_plan_for_problem(
    db: AsyncSession, problem_id: str
) -> Optional[ProblemPlan]:
    """Get the latest plan for a problem, preferring verified ones."""
    # First try to find a verified plan
    stmt = (
        select(ProblemPlan)
        .where(
            and_(
                ProblemPlan.problem_id == problem_id,
                ProblemPlan.verification_status == "verified",
            )
        )
        .order_by(ProblemPlan.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    plan = result.scalar_one_or_none()

    if plan:
        return plan

    # Fallback to any plan
    stmt = (
        select(ProblemPlan)
        .where(ProblemPlan.problem_id == problem_id)
        .order_by(ProblemPlan.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
