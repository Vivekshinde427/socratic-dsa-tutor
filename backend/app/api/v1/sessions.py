"""
Tutoring Session Endpoints (Milestone 2).
Handles session lifecycle, student interactions (MCQ, free-text, hint),
code execution via sandbox, and SSE streaming of validated tutor responses.
"""
import asyncio
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from backend.app.deps import get_current_user, get_db
from backend.app.db.models.user import User
from backend.app.schemas.session import (
    CodeRunRequest,
    CodeRunResultOut,
    FreeTextRequest,
    MCQAnswerRequest,
    MessageOut,
    SessionCreate,
    SessionDetail,
    SessionOut,
    TutorResponse,
)
from backend.app.services.session_service import (
    get_session_by_id,
    get_session_messages,
    get_user_sessions,
)
from backend.app.services.tutor_service import tutor_service

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=TutorResponse)
async def create_or_resume_session(
    payload: SessionCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Start a new tutoring session or resume an active one for a problem."""
    return await tutor_service.start_or_get_session(
        db=db, user_id=user.id, problem_id=payload.problem_id
    )


@router.get("", response_model=List[SessionOut])
async def list_user_sessions(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all tutoring sessions for the current user."""
    return await get_user_sessions(db=db, user_id=user.id, limit=limit)


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get detailed information about a specific session."""
    session = await get_session_by_id(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    if session.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )
    return session


@router.get("/{session_id}/messages", response_model=List[MessageOut])
async def get_messages(
    session_id: str,
    limit: int = Query(200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get chronological conversation messages for a session."""
    session = await get_session_by_id(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    if session.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )
    return await get_session_messages(db, session_id, limit=limit)


@router.post("/{session_id}/answer", response_model=TutorResponse)
async def submit_mcq_answer(
    session_id: str,
    payload: MCQAnswerRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Submit an answer to the current MCQ step. Server grades deterministically."""
    return await tutor_service.submit_mcq_answer(
        db=db,
        user_id=user.id,
        session_id=session_id,
        selected_option_id=payload.selected_option_id,
    )


@router.post("/{session_id}/message", response_model=TutorResponse)
async def send_free_text_message(
    session_id: str,
    payload: FreeTextRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Submit a free-text response. Evaluated via Socratic rubric; guarded before return."""
    return await tutor_service.submit_free_text(
        db=db,
        user_id=user.id,
        session_id=session_id,
        content=payload.content,
    )


@router.post("/{session_id}/hint", response_model=TutorResponse)
async def request_hint(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Request a hint for the current step ('I'm stuck'). Escalates hint level."""
    return await tutor_service.request_hint(
        db=db,
        user_id=user.id,
        session_id=session_id,
    )


@router.post("/{session_id}/code/run", response_model=CodeRunResultOut)
async def run_code(
    session_id: str,
    payload: CodeRunRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Run code in isolated sandbox subprocess without testing against hidden test cases."""
    return await tutor_service.execute_code(
        db=db,
        user_id=user.id,
        session_id=session_id,
        code=payload.code,
        language=payload.language,
        is_submission=False,
    )


@router.post("/{session_id}/code/submit", response_model=CodeRunResultOut)
async def submit_code(
    session_id: str,
    payload: CodeRunRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Submit code to run against verified test cases in isolated sandbox subprocess."""
    return await tutor_service.execute_code(
        db=db,
        user_id=user.id,
        session_id=session_id,
        code=payload.code,
        language=payload.language,
        is_submission=True,
    )


@router.get("/{session_id}/stream")
async def stream_free_text_response(
    session_id: str,
    content: str = Query(..., min_length=1, max_length=5000),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    SSE streaming endpoint for free-text tutor interactions.
    Validates complete response with Leak Guard BEFORE emitting any SSE event.
    """
    # 1. Generate and fully validate response
    response: TutorResponse = await tutor_service.submit_free_text(
        db=db,
        user_id=user.id,
        session_id=session_id,
        content=content,
    )

    async def event_generator():
        # Emit complete validated metadata event
        meta_data = {
            "response_type": response.response_type.value,
            "current_step_index": response.current_step_index,
            "session_status": response.session_status,
            "stage_progress": response.stage_progress,
        }
        yield {
            "event": "meta",
            "data": json.dumps(meta_data),
        }

        # Stream words with slight delay for smooth typing UX
        words = response.message.split(" ")
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            yield {
                "event": "delta",
                "data": json.dumps({"text": chunk}),
            }
            await asyncio.sleep(0.02)

        # Emit completion event
        yield {
            "event": "done",
            "data": json.dumps({"completed": True}),
        }

    return EventSourceResponse(event_generator())
