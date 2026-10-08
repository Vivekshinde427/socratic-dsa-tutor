# Socratic DSA Tutor - Progress Log

Status: MILESTONE 2 COMPLETE
Current milestone: 2 (Completed) -> Ready for Milestone 3

## Completed

### Milestone 1 - Backend Foundation + Verified Problem Planning
- Core architecture locked to supplied diagrams and roadmap.
- Python virtual environment `.venv` initialized with dependencies (`fastapi`, `pydantic v2`, `sqlalchemy 2`, `alembic`, `asyncpg`, `psycopg-binary`, `argon2-cffi`, `pyjwt`, `google-genai`, `pytest`, `pytest-asyncio`, `httpx`).
- PostgreSQL database connection configured (`DATABASE_URL` with asyncpg, `SYNC_DATABASE_URL` with psycopg for Alembic).
- SQLAlchemy 2 DeclarativeBase models created: `User`, `Problem`, `ProblemPlan`, and `SystemLog`.
- Alembic migrations initialized and executed (`791644889ceb_initial_schema.py`).
- Security module implemented with argon2 password hashing and JWT access token + httpOnly refresh token cookie lifecycle.
- Pydantic v2 schemas created for `TutoringPlan`, `Step`, `MCQOption`, `OptionFeedback`, `Hint`, `Approach`, `TestCase`, and `Misconception`.
- Client-safe DTOs (`ClientStepDTO`, `ClientProblemDTO`, `ClientPlanOverviewDTO`) ensuring hidden answer keys, correct option IDs, reference code, and raw expected outputs are never exposed to the client.
- Gemini LLM service boundary built with configurable model, temperature, retries, latency/token logging.
- Subprocess-based Python development sandbox implemented outside the FastAPI server process.
- Plan verifier service implemented executing reference and brute-force solutions in sandbox against generated test cases.

### Milestone 2 - Tutoring Engine + Complete Backend API
- **Database Models & Migrations (SPEC §17)**:
  - `Session` - Tutoring sessions linked to user + problem with step position, hint level, attempts, stage progress, and rolling summary.
  - `Message` - Chronological conversation history within tutoring sessions (roles: student, tutor, system).
  - `Feedback` - Student rating and feedback comments on sessions.
  - `LearningProgress` - Per-user per-topic explainable mastery tracking (SPEC §15) in [0.0, 1.0].
  - `MCQAttempt` - Per-attempt tracking of student choices, correctness, and misconception IDs.
  - `CodeRun` - Code execution records capturing status, runtime, test counts, and results.
  - Alembic migration `8f102711ab4d_add_milestone_2_tutoring_tables.py` added for PostgreSQL environments.
- **Pydantic Schemas (`backend/app/schemas/session.py`)**:
  - `SessionCreate`, `SessionOut`, `SessionDetail`.
  - `MessageOut`, `MCQAnswerRequest`, `FreeTextRequest`, `HintRequest`.
  - `MCQResultOut`, `EvaluationClassification`, `EvaluationResult`, `TutorResponse`.
  - `CodeRunRequest`, `CodeRunResultOut`.
  - `LearningProgressOut`.
- **LangGraph Tutoring Engine (`backend/app/services/tutoring_graph.py`)**:
  - StateGraph workflow implementing Diagram 1 with typed state `TutoringState`.
  - Nodes: `load_context`, `route_intent`, `present_step`, `evaluate`, `further_guidance`, `update_progress`, `formative_feedback`, `deflect`, and `guard`.
  - Deterministic MCQ grading and structured rubric-based free-text evaluation.
  - Socratic deflection path for solution-seeking requests and jailbreaks.
- **Leak Guard Service (`backend/app/services/leak_guard.py`)**:
  - 3-tier inspection pipeline (SPEC §12): Regex/AST multi-statement inspection, reference token overlap similarity, and LLM judge.
  - Verified blocking of full code solutions, multi-line code loops, and high similarity text.
  - Verified pass-through of Socratic nudges, questions, and scaffold skeletons with blanks (`___`).
  - Fallback safe question substitution if generated response fails guard.
- **Core Educational Services**:
  - `mcq_service.py`: Server-side deterministic grading, never sending `correct_option_id` to client.
  - `evaluator.py`: Free-text evaluation against learning criteria with regex pre-checks.
  - `hint_service.py`: 4-level hint escalation ladder with scaffold blanks at Level 4.
  - `mastery_service.py`: Explainable Bayesian/heuristic mastery updates per user per topic.
  - `context_manager.py`: Sliding window (recent 6-8 turns), topic mastery, and rolling summaries.
  - `session_service.py`: Session, message, and plan retrieval helpers.
  - `tutor_service.py`: Central orchestrator uniting LangGraph, database, sandbox execution, and mastery updates.
- **API Endpoints (27 total endpoints mounted in FastAPI)**:
  - `POST /api/v1/sessions` - Start or resume tutoring session.
  - `GET /api/v1/sessions` - List user sessions.
  - `GET /api/v1/sessions/{id}` - Session details.
  - `GET /api/v1/sessions/{id}/messages` - Message history.
  - `POST /api/v1/sessions/{id}/answer` - Grade student MCQ answer.
  - `POST /api/v1/sessions/{id}/message` - Free-text response with Leak Guard.
  - `POST /api/v1/sessions/{id}/hint` - Escalate hint ladder.
  - `POST /api/v1/sessions/{id}/code/run` - Run code in isolated sandbox.
  - `POST /api/v1/sessions/{id}/code/submit` - Submit code against hidden test cases.
  - `GET /api/v1/sessions/{id}/stream` - SSE streaming endpoint for validated tutor responses.
  - `GET /api/v1/progress/me` - Topic progress and mastery values.
  - `GET /api/v1/progress/recommendations` - Adaptive topic/problem recommendations based on mastery gaps.
  - `GET /api/v1/admin/users`, `PATCH /api/v1/admin/users/{id}`, `GET /api/v1/admin/metrics` - Admin platform management.
- **Contract Export**:
  - Generated and validated `openapi.json` contract for frontend handoff.
- **Automated Test Suite**:
  - 38 passed, 1 skipped (live Gemini provider test).
  - Full 12-step synthetic student tutoring journey test passed (`test_tutoring_journey.py`).
  - Leak Guard regression tests passed (`test_leak_guard.py`).
  - MCQ grading & hint ladder escalation tests passed (`test_mcq_and_hints.py`).

## Current work
Milestone 2 is complete. Pausing at the milestone boundary as required by agent rules.

## Known issues
None. All 38 automated unit/integration tests pass with 0 warnings.

## Next action
Begin **Milestone 3** according to prompt specifications:
1. Frontend application development with React and Vite.
2. Socratic dialogue interface, code editor (Monaco), stage progress visualizer, and hint panel.
3. Integration with the 27 backend endpoints defined in `openapi.json`.

## Change log
- Milestone 1: Backend foundation, PostgreSQL schema, auth & roles, problem & plan persistence, typed contracts, Gemini service boundary, sandbox executor, plan verifier.
- Milestone 2: Tutoring Engine with LangGraph workflow, Leak Guard, deterministic MCQ grading, 4-level hint ladder, code sandbox execution, learning progress/mastery updates, SSE streaming, complete API routes, openapi.json, and full 12-step synthetic journey automated tests.
