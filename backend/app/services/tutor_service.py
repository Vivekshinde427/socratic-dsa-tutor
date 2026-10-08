"""
High-level Socratic Tutor Orchestrator (Milestone 2).
Coordinates DB sessions, messages, LangGraph workflow execution,
code execution via sandbox, and mastery tracking.
"""
import json
from typing import Any, Dict, List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from backend.app.core.logging import logger
from backend.app.db.models.code_run import CodeRun
from backend.app.db.models.message import Message
from backend.app.db.models.problem import Problem
from backend.app.db.models.problem_plan import ProblemPlan
from backend.app.db.models.session import Session
from backend.app.schemas.session import (
    CodeRunResultOut,
    MCQResultOut,
    TutorResponse,
    TutorResponseType,
)
from backend.app.schemas.tutoring_plan import (
    ClientStepDTO,
    Step,
    TutoringPlan,
)
from backend.app.services.context_manager import context_manager
from backend.app.services.mastery_service import mastery_service
from backend.app.services.sandbox.base import ExecutionRequest, ExecutionStatus
from backend.app.services.sandbox.development_executor import development_sandbox
from backend.app.services.session_service import (
    add_message,
    create_session,
    get_latest_plan_for_problem,
    get_recent_messages,
    get_session_by_id,
)
from backend.app.services.tutoring_graph import tutoring_graph
from backend.app.services.verifier import HARNESS_TEMPLATE


class TutorService:
    """Coordinates tutoring interactions, graph invocation, and persistence."""

    async def _get_active_session_and_plan(
        self, db: AsyncSession, user_id: str, session_id: str
    ) -> tuple[Session, Problem, Optional[TutoringPlan]]:
        """Validates ownership and loads session, problem, and plan."""
        session = await get_session_by_id(db, session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        if session.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this session")

        problem_stmt = select(Problem).where(Problem.id == session.problem_id)
        problem_res = await db.execute(problem_stmt)
        problem = problem_res.scalar_one_or_none()
        if not problem:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found")

        plan: Optional[TutoringPlan] = None
        if session.plan_id:
            plan_stmt = select(ProblemPlan).where(ProblemPlan.id == session.plan_id)
            plan_res = await db.execute(plan_stmt)
            plan_row = plan_res.scalar_one_or_none()
            if plan_row:
                plan = TutoringPlan.model_validate(plan_row.plan_dict)

        if not plan:
            plan_row = await get_latest_plan_for_problem(db, problem.id)
            if plan_row:
                session.plan_id = plan_row.id
                plan = TutoringPlan.model_validate(plan_row.plan_dict)

        return session, problem, plan

    def _get_current_step(self, plan: Optional[TutoringPlan], step_idx: int) -> Optional[Step]:
        if not plan or not plan.socratic_steps:
            return None
        if 0 <= step_idx < len(plan.socratic_steps):
            return plan.socratic_steps[step_idx]
        return None

    async def start_or_get_session(
        self, db: AsyncSession, user_id: str, problem_id: str
    ) -> TutorResponse:
        """Starts a new session or resumes the latest active session for a problem."""
        # Find active session
        stmt = (
            select(Session)
            .where(
                and_(
                    Session.user_id == user_id,
                    Session.problem_id == problem_id,
                    Session.status == "active",
                )
            )
            .order_by(Session.created_at.desc())
            .limit(1)
        )
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()

        problem_stmt = select(Problem).where(Problem.id == problem_id)
        problem_res = await db.execute(problem_stmt)
        problem = problem_res.scalar_one_or_none()
        if not problem:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found")

        plan_row = await get_latest_plan_for_problem(db, problem_id)
        plan_dict = plan_row.plan_dict if plan_row else None
        plan = TutoringPlan.model_validate(plan_dict) if plan_dict else None

        if not session:
            session = await create_session(
                db=db,
                user_id=user_id,
                problem_id=problem_id,
                plan_id=plan_row.id if plan_row else None,
            )
            # Track problem attempt in mastery service
            if problem.topics:
                await mastery_service.record_problem_attempt(db, user_id, problem.topics, completed=False)

        current_step = self._get_current_step(plan, session.current_step_index)

        # Invoke LangGraph to prepare initial presentation
        graph_input = {
            "session_id": session.id,
            "user_id": user_id,
            "problem_id": problem.id,
            "problem_title": problem.title,
            "problem_topics": problem.topics or [],
            "plan_dict": plan_dict,
            "current_step_index": session.current_step_index,
            "current_hint_level": session.current_hint_level,
            "attempts": session.current_attempts,
            "input_type": "start",
            "student_input": "",
            "stage_progress": session.stage_progress or {},
            "session_status": session.status,
        }

        output = await tutoring_graph.ainvoke(graph_input)

        # Update session with graph state
        session.stage_progress = output.get("stage_progress", session.stage_progress)
        session.status = output.get("session_status", session.status)
        await db.commit()
        await db.refresh(session)

        # Add initial tutor message
        tutor_msg = output.get("response_message", "")
        await add_message(
            db=db,
            session_id=session.id,
            role="tutor",
            content=tutor_msg,
            message_type=output.get("response_type", "mcq_step"),
            step_index=session.current_step_index,
        )
        await db.commit()

        step_dto = None
        if output.get("step_data"):
            step_dto = ClientStepDTO.model_validate(output["step_data"])

        return TutorResponse(
            response_type=TutorResponseType(output.get("response_type", "mcq_step")),
            message=tutor_msg,
            step=step_dto,
            current_step_index=session.current_step_index,
            current_stage=current_step.stage if current_step else None,
            hint_level=session.current_hint_level,
            stage_progress=session.stage_progress,
            session_status=session.status,
        )

    async def submit_mcq_answer(
        self, db: AsyncSession, user_id: str, session_id: str, selected_option_id: str
    ) -> TutorResponse:
        """Processes student MCQ answer through LangGraph and persists results."""
        session, problem, plan = await self._get_active_session_and_plan(db, user_id, session_id)
        current_step = self._get_current_step(plan, session.current_step_index)
        if not current_step:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active step in session")

        # Record student message
        await add_message(
            db=db,
            session_id=session.id,
            role="student",
            content=f"Selected option: {selected_option_id.upper()}",
            message_type="mcq_answer",
            metadata_json={"selected_option_id": selected_option_id.upper()},
            step_index=session.current_step_index,
        )

        plan_dict = plan.model_dump() if plan else None

        # Run LangGraph
        graph_input = {
            "session_id": session.id,
            "user_id": user_id,
            "problem_id": problem.id,
            "problem_title": problem.title,
            "problem_topics": problem.topics or [],
            "plan_dict": plan_dict,
            "current_step_index": session.current_step_index,
            "current_hint_level": session.current_hint_level,
            "attempts": session.current_attempts,
            "input_type": "mcq",
            "selected_option_id": selected_option_id,
            "stage_progress": session.stage_progress or {},
            "session_status": session.status,
        }

        output = await tutoring_graph.ainvoke(graph_input)

        is_understood = output.get("is_understood", False)
        mcq_result_dict = output.get("mcq_result")

        # Update mastery in DB
        first_try = (session.current_attempts == 0)
        for topic in (problem.topics or []):
            await mastery_service.update_mastery(
                db=db,
                user_id=user_id,
                topic=topic,
                correct=is_understood,
                hint_level=session.current_hint_level,
                first_try=first_try,
            )

        # Update session state
        session.current_step_index = output.get("current_step_index", session.current_step_index)
        session.current_hint_level = output.get("current_hint_level", session.current_hint_level)
        session.stage_progress = output.get("stage_progress", session.stage_progress)
        session.status = output.get("session_status", session.status)
        session.current_attempts = output.get("attempts", session.current_attempts)

        if is_understood:
            session.current_attempts = 0
            if session.status == "completed" and problem.topics:
                await mastery_service.record_problem_attempt(db, user_id, problem.topics, completed=True)

        # Persist tutor message
        tutor_msg = output.get("response_message", "")
        await add_message(
            db=db,
            session_id=session.id,
            role="tutor",
            content=tutor_msg,
            message_type=output.get("response_type", "mcq_result"),
            step_index=session.current_step_index,
        )
        await db.commit()
        await db.refresh(session)

        # Check for new active step to present if student advanced
        step_dto = None
        new_step = self._get_current_step(plan, session.current_step_index)
        if output.get("step_data"):
            step_dto = ClientStepDTO.model_validate(output["step_data"])
        elif is_understood and new_step:
            step_dto = ClientStepDTO.from_step(new_step)

        mcq_result_out = None
        if mcq_result_dict:
            mcq_result_out = MCQResultOut(
                correct=mcq_result_dict.get("correct", False),
                selected_option_id=mcq_result_dict.get("selected_option_id", ""),
                feedback=mcq_result_dict.get("feedback", ""),
                misconception_id=mcq_result_dict.get("misconception_id"),
            )

        return TutorResponse(
            response_type=TutorResponseType(output.get("response_type", "mcq_result")),
            message=tutor_msg,
            step=step_dto,
            mcq_result=mcq_result_out,
            current_step_index=session.current_step_index,
            current_stage=new_step.stage if new_step else None,
            hint_level=session.current_hint_level,
            stage_progress=session.stage_progress,
            session_status=session.status,
        )

    async def submit_free_text(
        self, db: AsyncSession, user_id: str, session_id: str, content: str
    ) -> TutorResponse:
        """Processes student free-text message through LangGraph with deflection & Leak Guard."""
        session, problem, plan = await self._get_active_session_and_plan(db, user_id, session_id)
        current_step = self._get_current_step(plan, session.current_step_index)

        # Record student message
        await add_message(
            db=db,
            session_id=session.id,
            role="student",
            content=content,
            message_type="free_text",
            step_index=session.current_step_index,
        )

        plan_dict = plan.model_dump() if plan else None

        # Run LangGraph
        graph_input = {
            "session_id": session.id,
            "user_id": user_id,
            "problem_id": problem.id,
            "problem_title": problem.title,
            "problem_topics": problem.topics or [],
            "plan_dict": plan_dict,
            "current_step_index": session.current_step_index,
            "current_hint_level": session.current_hint_level,
            "attempts": session.current_attempts,
            "input_type": "free_text",
            "student_input": content,
            "stage_progress": session.stage_progress or {},
            "session_status": session.status,
        }

        output = await tutoring_graph.ainvoke(graph_input)

        is_understood = output.get("is_understood", False)

        # Update session state
        session.current_step_index = output.get("current_step_index", session.current_step_index)
        session.current_hint_level = output.get("current_hint_level", session.current_hint_level)
        session.stage_progress = output.get("stage_progress", session.stage_progress)
        session.status = output.get("session_status", session.status)
        session.current_attempts = output.get("attempts", session.current_attempts)

        if is_understood:
            session.current_attempts = 0
            if session.status == "completed" and problem.topics:
                await mastery_service.record_problem_attempt(db, user_id, problem.topics, completed=True)

        # Persist tutor message
        tutor_msg = output.get("response_message", "")
        await add_message(
            db=db,
            session_id=session.id,
            role="tutor",
            content=tutor_msg,
            message_type=output.get("response_type", "free_text_response"),
            step_index=session.current_step_index,
        )

        # Periodically update rolling summary
        recent = await get_recent_messages(db, session.id)
        await context_manager.maybe_update_rolling_summary(db, session, recent)

        await db.commit()
        await db.refresh(session)

        step_dto = None
        new_step = self._get_current_step(plan, session.current_step_index)
        if output.get("step_data"):
            step_dto = ClientStepDTO.model_validate(output["step_data"])
        elif is_understood and new_step:
            step_dto = ClientStepDTO.from_step(new_step)

        return TutorResponse(
            response_type=TutorResponseType(output.get("response_type", "free_text_response")),
            message=tutor_msg,
            step=step_dto,
            current_step_index=session.current_step_index,
            current_stage=new_step.stage if new_step else None,
            hint_level=session.current_hint_level,
            stage_progress=session.stage_progress,
            session_status=session.status,
        )

    async def request_hint(
        self, db: AsyncSession, user_id: str, session_id: str
    ) -> TutorResponse:
        """Processes explicit student hint request ('I'm stuck')."""
        session, problem, plan = await self._get_active_session_and_plan(db, user_id, session_id)
        current_step = self._get_current_step(plan, session.current_step_index)
        if not current_step:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active step")

        # Record student message
        await add_message(
            db=db,
            session_id=session.id,
            role="student",
            content="I need a hint.",
            message_type="hint_request",
            step_index=session.current_step_index,
        )

        plan_dict = plan.model_dump() if plan else None

        # Run LangGraph with hint intent
        graph_input = {
            "session_id": session.id,
            "user_id": user_id,
            "problem_id": problem.id,
            "problem_title": problem.title,
            "problem_topics": problem.topics or [],
            "plan_dict": plan_dict,
            "current_step_index": session.current_step_index,
            "current_hint_level": session.current_hint_level,
            "attempts": session.current_attempts,
            "input_type": "hint",
            "student_input": "I'm stuck, please give me a hint.",
            "stage_progress": session.stage_progress or {},
            "session_status": session.status,
        }

        output = await tutoring_graph.ainvoke(graph_input)

        session.current_hint_level = output.get("current_hint_level", session.current_hint_level)

        tutor_msg = output.get("response_message", "")
        await add_message(
            db=db,
            session_id=session.id,
            role="tutor",
            content=tutor_msg,
            message_type="hint",
            step_index=session.current_step_index,
        )
        await db.commit()
        await db.refresh(session)

        return TutorResponse(
            response_type=TutorResponseType.hint,
            message=tutor_msg,
            current_step_index=session.current_step_index,
            current_stage=current_step.stage,
            hint_level=session.current_hint_level,
            stage_progress=session.stage_progress,
            session_status=session.status,
        )

    async def execute_code(
        self,
        db: AsyncSession,
        user_id: str,
        session_id: str,
        code: str,
        language: str = "python",
        is_submission: bool = False,
    ) -> CodeRunResultOut:
        """
        Executes student code in isolated sandbox subprocess outside FastAPI.
        If is_submission=True, tests against plan test cases.
        """
        session, problem, plan = await self._get_active_session_and_plan(db, user_id, session_id)

        if not is_submission:
            # Simple run: execute code directly
            exec_res = await development_sandbox.execute(
                ExecutionRequest(code=code, language=language, timeout_seconds=5.0)
            )

            # Record run in DB
            code_run = CodeRun(
                session_id=session.id,
                user_id=user_id,
                code=code,
                language=language,
                run_type="run",
                status=exec_res.status.value,
                stdout=exec_res.stdout,
                stderr=exec_res.stderr,
                execution_time_ms=exec_res.execution_time_ms,
            )
            db.add(code_run)
            await db.commit()

            return CodeRunResultOut(
                status=exec_res.status.value,
                stdout=exec_res.stdout,
                stderr=exec_res.stderr,
                execution_time_ms=exec_res.execution_time_ms,
            )

        # Submission run: execute against plan's test cases
        test_cases = plan.test_cases if plan else []
        if not test_cases:
            # Fallback to plain run if no test cases in plan
            exec_res = await development_sandbox.execute(
                ExecutionRequest(code=code, language=language, timeout_seconds=5.0)
            )
            code_run = CodeRun(
                session_id=session.id,
                user_id=user_id,
                code=code,
                language=language,
                run_type="submit",
                status=exec_res.status.value,
                stdout=exec_res.stdout,
                stderr=exec_res.stderr,
                execution_time_ms=exec_res.execution_time_ms,
                tests_passed=1 if exec_res.status == ExecutionStatus.SUCCESS else 0,
                tests_total=1,
            )
            db.add(code_run)
            await db.commit()
            return CodeRunResultOut(
                status=exec_res.status.value,
                stdout=exec_res.stdout,
                stderr=exec_res.stderr,
                execution_time_ms=exec_res.execution_time_ms,
                tests_passed=1 if exec_res.status == ExecutionStatus.SUCCESS else 0,
                tests_total=1,
            )

        passed_count = 0
        total_count = len(test_cases)
        results_map = {}
        total_time_ms = 0.0

        for idx, tc in enumerate(test_cases):
            # Build execution harness script for this test case
            harness = HARNESS_TEMPLATE.replace("__CODE__", code).replace(
                "__TEST_INPUT_REPR__", repr(tc.input)
            )
            exec_res = await development_sandbox.execute(
                ExecutionRequest(code=harness, language=language, timeout_seconds=4.0)
            )
            total_time_ms += exec_res.execution_time_ms

            if exec_res.status != ExecutionStatus.SUCCESS:
                results_map[f"test_{idx + 1}"] = {
                    "passed": False,
                    "category": tc.category.value,
                    "error": exec_res.stderr or exec_res.status.value,
                }
                continue

            try:
                actual = json.loads(exec_res.stdout.strip())
                expected = json.loads(tc.expected_output.strip())
                is_tc_pass = (actual == expected)
            except Exception:
                is_tc_pass = (exec_res.stdout.strip() == tc.expected_output.strip())

            if is_tc_pass:
                passed_count += 1
                results_map[f"test_{idx + 1}"] = {
                    "passed": True,
                    "category": tc.category.value,
                }
            else:
                results_map[f"test_{idx + 1}"] = {
                    "passed": False,
                    "category": tc.category.value,
                    "error": "Wrong answer",
                }

        all_passed = (passed_count == total_count)
        overall_status = "success" if all_passed else "failed"

        # Record submission in DB
        code_run = CodeRun(
            session_id=session.id,
            user_id=user_id,
            code=code,
            language=language,
            run_type="submit",
            status=overall_status,
            execution_time_ms=total_time_ms,
            tests_passed=passed_count,
            tests_total=total_count,
            test_results=results_map,
        )
        db.add(code_run)

        # If all passed, record problem completion in mastery service
        if all_passed and problem.topics:
            await mastery_service.record_problem_attempt(
                db, user_id, problem.topics, completed=True
            )

        await db.commit()

        return CodeRunResultOut(
            status=overall_status,
            stdout=f"{passed_count}/{total_count} tests passed",
            stderr="",
            execution_time_ms=total_time_ms,
            tests_passed=passed_count,
            tests_total=total_count,
            test_results=results_map,
        )


tutor_service = TutorService()
