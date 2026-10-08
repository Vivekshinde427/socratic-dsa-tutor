"""
Tests for MCQ deterministic grading and hint ladder escalation (Milestone 2).
Verifies:
- Server grades MCQ deterministically against correct_option_id
- correct_option_id is NEVER exposed in client responses
- Hint ladder escalates 1 level per request up to Level 4
- Level 4 hint contains blanks/gaps and does not expose complete code
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.session import Session
from backend.app.schemas.tutoring_plan import Hint, MCQOption, OptionFeedback, SocraticStage, Step
from backend.app.services.hint_service import hint_service
from backend.app.services.mcq_service import mcq_service


@pytest.fixture
def sample_step() -> Step:
    return Step(
        id="step_1",
        stage=SocraticStage.understand,
        question="What does the Two Sum problem ask you to return?",
        options=[
            MCQOption(id="A", text="The two numbers themselves"),
            MCQOption(id="B", text="The indices of the two numbers"),
            MCQOption(id="C", text="The sum of all numbers"),
            MCQOption(id="D", text="A boolean indicating if pair exists"),
        ],
        correct_option_id="B",
        option_feedback=[
            OptionFeedback(option_id="A", why_wrong="The question specifically asks for indices, not values.", misconception_id="confuse_index_and_value"),
            OptionFeedback(option_id="C", why_wrong="We want the positions of the pair, not a total sum.", misconception_id="confuse_goal"),
            OptionFeedback(option_id="D", why_wrong="We need the specific positions [i, j], not just True/False.", misconception_id="confuse_return_type"),
        ],
        hint_ladder=[
            Hint(level=1, content="Read the return specification carefully."),
            Hint(level=2, content="Look at example 1: nums = [2,7,11,15], target = 9 -> output: [0,1]."),
            Hint(level=3, content="The output consists of zero-based array positions."),
            Hint(level=4, content="Scaffold:\nreturn [index1, ___]"),
        ],
        success_criteria=["Identifies that indices must be returned"],
    )


@pytest.mark.asyncio
async def test_mcq_deterministic_correct_grading(db_session: AsyncSession, sample_step: Step):
    session = Session(
        user_id="user_123",
        problem_id="prob_123",
        current_step_index=0,
        current_hint_level=0,
    )
    db_session.add(session)
    await db_session.flush()

    res = await mcq_service.evaluate_answer(
        db=db_session,
        session=session,
        step=sample_step,
        selected_option_id="B",
    )

    assert res.correct is True
    assert res.selected_option_id == "B"
    # Ensure correct_option_id is NOT a field on the response DTO
    assert not hasattr(res, "correct_option_id")


@pytest.mark.asyncio
async def test_mcq_deterministic_incorrect_grading(db_session: AsyncSession, sample_step: Step):
    session = Session(
        user_id="user_123",
        problem_id="prob_123",
        current_step_index=0,
        current_hint_level=0,
    )
    db_session.add(session)
    await db_session.flush()

    res = await mcq_service.evaluate_answer(
        db=db_session,
        session=session,
        step=sample_step,
        selected_option_id="A",
    )

    assert res.correct is False
    assert res.selected_option_id == "A"
    assert "indices, not values" in res.feedback
    assert res.misconception_id == "confuse_index_and_value"
    assert not hasattr(res, "correct_option_id")


@pytest.mark.asyncio
async def test_hint_ladder_escalation(db_session: AsyncSession, sample_step: Step):
    session = Session(
        user_id="user_123",
        problem_id="prob_123",
        current_step_index=0,
        current_hint_level=0,
    )
    db_session.add(session)
    await db_session.flush()

    # Level 1
    lvl1, text1 = await hint_service.escalate_hint(db_session, session, sample_step)
    assert lvl1 == 1
    assert session.current_hint_level == 1
    assert "Read the return specification" in text1

    # Level 2
    lvl2, text2 = await hint_service.escalate_hint(db_session, session, sample_step)
    assert lvl2 == 2
    assert session.current_hint_level == 2
    assert "example 1" in text2

    # Level 3
    lvl3, text3 = await hint_service.escalate_hint(db_session, session, sample_step)
    assert lvl3 == 3
    assert session.current_hint_level == 3
    assert "zero-based" in text3

    # Level 4
    lvl4, text4 = await hint_service.escalate_hint(db_session, session, sample_step)
    assert lvl4 == 4
    assert session.current_hint_level == 4
    assert "___" in text4

    # Cap at Level 4
    lvl5, text5 = await hint_service.escalate_hint(db_session, session, sample_step)
    assert lvl5 == 4
    assert session.current_hint_level == 4
