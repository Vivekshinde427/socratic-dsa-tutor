# Antigravity Milestone 1 - Backend Foundation + Verified Problem Planning

You are implementing Milestone 1 of the Socratic DSA Tutor.

## Before touching code
Read, in this order:
1. `AGENTS.md`
2. `SPEC.md`
3. `PLAN.md`
4. `PROGRESS.md`
5. `DECISIONS.md`
6. `contracts/tutoring_plan_contract.md`

Also inspect the current repository tree. If the repo already contains valid work, preserve it and continue rather than recreating files.

## Scope
Implement **only Milestone 1** from `PLAN.md`:
- repository/environment foundation
- FastAPI boot
- PostgreSQL + SQLAlchemy + Alembic
- authentication and roles
- problems/problem_plans persistence
- Pydantic tutoring-plan contracts
- Gemini service boundary
- Problem Analyst generation
- sandbox abstraction
- verification pipeline
- tests

Do not implement the full Socratic session loop yet. Do not build the final frontend yet. Do not add RAG, deployment, MCP, unrelated abstractions, or speculative features.

## Technical requirements
- Python 3.11+
- FastAPI
- Pydantic v2
- SQLAlchemy 2
- Alembic
- PostgreSQL
- Gemini behind a service interface with configurable model name
- Structured JSON output validated by Pydantic
- Retry/backoff and error handling around LLM calls
- Logging of latency and token metadata where available
- Password hashing with argon2/bcrypt
- JWT access + refresh lifecycle using secure httpOnly refresh cookie semantics
- Role support for student/admin
- No personal data sent to Gemini beyond what the minimum feature requires; prefer opaque IDs

## Required backend structure
Use the repository structure defined by `SPEC.md`. Keep route handlers thin and business rules in services.

At minimum, establish:
- `backend/app/main.py`
- `backend/app/config.py`
- `backend/app/deps.py`
- `backend/app/api/`
- `backend/app/core/`
- `backend/app/db/`
- `backend/app/schemas/`
- `backend/app/services/`
- `backend/app/prompts/`
- `backend/tests/`

## Tutoring plan implementation
Create typed Pydantic models for `TutoringPlan`, `Step`, `MCQOption`, option feedback, hints, approaches, examples, test cases, and misconceptions.

Keep server-only fields clearly separated from client-safe response models.

The Problem Analyst must produce a complete hidden plan, not student-facing tutor prose.

## Verification implementation
Build the verifier around a sandbox interface.

The verifier must be able to:
- execute reference and brute-force solutions against generated/provided tests
- compare outputs
- mark the plan verified only after all required checks pass
- mark verification failure explicitly

Do not silently treat an execution failure as a passing verification.

For the Windows developer experience, make sandbox implementation configurable. It is acceptable to begin with a Python-only locked-down development executor if the production-style Judge0 path is not available locally, but the code must never execute untrusted student code in the FastAPI process.

## Required smoke test
Use a classic two-sum-style DSA problem, expressed in the team's own words, and create a deterministic integration test that demonstrates:
1. problem persisted
2. plan schema validation
3. brute-force/reference verification
4. verified flag becomes true for a known-good plan
5. deliberately wrong reference behavior is rejected or marked unverified

Do not require a live Gemini API in every unit test. Mock the provider boundary. Add one clearly separated live-provider smoke test that is skipped unless an API key is configured.

## Done conditions
Before stopping:
- Run all relevant tests and fix failures.
- Confirm Alembic migration works from a clean database.
- Confirm FastAPI `/docs` is available.
- Confirm auth flow tests pass.
- Confirm plan verification tests pass.
- Export or document the current API contract if practical.
- Update `PROGRESS.md` with exact completed items, tests run, remaining issues, and the instruction to start Milestone 2 next.
- List every file changed.
- Stop. Do not start Milestone 2.
