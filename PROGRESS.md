# Socratic DSA Tutor - Progress Log

Status: MILESTONE 1 COMPLETE
Current milestone: 1 (Completed) -> Ready for Milestone 2

## Completed
- Project source diagrams supplied and reviewed.
- Project roadmap/specification supplied and reviewed.
- Core architecture locked to supplied diagrams and roadmap.
- **Milestone 1 - Backend Foundation + Verified Problem Planning**:
  - Python virtual environment `.venv` initialized with dependencies (`fastapi`, `pydantic v2`, `sqlalchemy 2`, `alembic`, `asyncpg`, `psycopg-binary`, `argon2-cffi`, `pyjwt`, `google-genai`, `pytest`, `pytest-asyncio`, `httpx`).
  - PostgreSQL database connection configured (`DATABASE_URL` with asyncpg, `SYNC_DATABASE_URL` with psycopg for Alembic).
  - SQLAlchemy 2 DeclarativeBase models created: `User`, `Problem`, `ProblemPlan`, and `SystemLog`.
  - Alembic migrations initialized and executed cleanly (`791644889ceb_initial_schema.py`); verified bidirectional migration apply (`downgrade base` and `upgrade head`).
  - Security module implemented with argon2 password hashing and JWT access token + httpOnly refresh token cookie lifecycle.
  - Pydantic v2 schemas created for `TutoringPlan`, `Step`, `MCQOption`, `OptionFeedback`, `Hint`, `Approach`, `TestCase`, and `Misconception` with strict validation (e.g. `correct_option_id` membership in options, minimum 2 options).
  - Client-safe DTOs (`ClientStepDTO`, `ClientProblemDTO`, `ClientPlanOverviewDTO`) ensuring hidden answer keys, correct option IDs, reference code, and raw expected outputs are never exposed to the client.
  - Gemini LLM service boundary built with configurable model, temperature, retries with exponential backoff, latency/token logging, and mock/isolated support.
  - Versioned Problem Analyst prompt (`v1.0.0`) authored strictly enforcing the hidden pedagogical plan generation.
  - Plan generation service coordinating LLM calls and Pydantic validation.
  - Subprocess-based Python development sandbox implemented enforcing execution timeout, bounded stdio buffers, and process isolation outside the FastAPI server process.
  - Plan verifier service implemented executing reference and brute-force solutions against generated test cases in the sandbox, verifying output agreement, and setting verification status (`verified` or `verification_failed`).
  - API routers implemented and mounted:
    - `GET /health` and `GET /api/v1/health`
    - `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh`, `POST /api/v1/auth/logout`, `GET /api/v1/auth/me`
    - `GET /api/v1/users/me`, `PUT /api/v1/users/me`
    - `GET /api/v1/problems`, `GET /api/v1/problems/{id}`, `POST /api/v1/problems/paste`
    - `POST /api/v1/admin/problems/{id}/regenerate-plan`, `GET /api/v1/admin/logs`
  - Automated tests implemented with 100% pass rate:
    - `test_health.py`: 2 passed
    - `test_auth.py`: 8 passed
    - `test_plan_contract.py`: 4 passed
    - `test_sandbox.py`: 6 passed
    - `test_verifier.py`: 5 passed
    - `test_problems_api.py`: 2 passed
    - `test_two_sum_smoke.py`: 1 passed (full 5-part deterministic smoke integration)
    - `test_gemini_live.py`: 1 skipped (live provider test, skipped when API key not set)
    - Total: 28 passed, 1 skipped, 0 warnings.
  - OpenAPI 3.1 schema exported to `contracts/openapi_milestone_1.json` (13 endpoints documented).

## Current work
Milestone 1 is complete. Pausing at the milestone boundary as required by agent rules.

## Known issues
None. All 28 automated unit/integration tests pass with 0 warnings. Live Gemini tests require `GEMINI_API_KEY` environment variable if running against live Google servers.

## Next action
Begin **Milestone 2 - Tutoring Engine + Full Backend API** following `prompts/02_tutoring_engine.md`:
1. Implement the LangGraph typed state representing Diagram 1.
2. Build the LangGraph workflow nodes: `load_context`, `route_intent`, `get_or_create_plan`, `present_step`, `await_student`, `evaluate`, `conditional understood?`, `further_guidance`, `formative_feedback`, `update_progress`, and deflection path.
3. Build the deterministic MCQ grading engine and free-text rubric evaluation.
4. Implement the hint escalation ladder (levels 0-4).
5. Implement the Leak Guard pipeline (regex/AST inspection, reference similarity, safe fallback).
6. Implement sessions, messages, feedback persistence, and learning progress tracking.
7. Implement Server-Sent Events (SSE) streaming for free-text tutor responses.
8. Implement code execution endpoints (`/sessions/{id}/code/run` and `/sessions/{id}/code/submit`).

## Change log
- Initial control pack created.
- Milestone 1 executed: backend foundation, PostgreSQL schema, auth & roles, problem & plan persistence, typed contracts, Gemini service boundary, sandbox executor, plan verifier, and comprehensive test suite.
