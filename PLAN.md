# Socratic DSA Tutor - Implementation Plan

## Milestone 1 - Backend Foundation + Verified Problem Planning

### Goal
Produce a runnable backend with PostgreSQL, authentication, the typed tutoring-plan contract, Gemini service boundary, Problem Analyst, sandbox boundary, verifier, and a proven plan-generation/verification path.

### Checklist
- [ ] Repository scaffolding and environment configuration
- [ ] FastAPI application boot and health endpoint
- [ ] PostgreSQL connection and SQLAlchemy setup
- [ ] Alembic migrations
- [ ] Users, auth, roles, token lifecycle
- [ ] Problem and problem-plan persistence
- [ ] Pydantic TutoringPlan/Step/MCQ contracts
- [ ] Gemini client service with retries/backoff/logging
- [ ] Versioned Problem Analyst prompt
- [ ] Plan generation service
- [ ] Sandbox abstraction
- [ ] Plan verifier
- [ ] Admin plan regeneration foundation
- [ ] Unit/integration tests
- [ ] Two Sum smoke plan generation + verification test

### Exit criteria
- `GET /health` works.
- Database migrations apply cleanly.
- Register/login/me works.
- A DSA problem can be persisted.
- A model-generated plan validates against Pydantic.
- A known-good plan can be verified in the sandbox.
- A deliberately wrong plan/reference implementation is rejected or marked unverified.
- No student-facing tutoring loop is claimed complete yet.

## Milestone 2 - Tutoring Engine + Full Backend API

### Goal
Implement the Diagram 1 loop with LangGraph, deterministic MCQ grading, free-text evaluation, hint ladder, Leak Guard, progress tracking, context management, SSE, code execution endpoints, and the complete API.

### Checklist
- [ ] LangGraph typed state
- [ ] load_context
- [ ] route_intent
- [ ] get_or_create_plan
- [ ] present_step
- [ ] await_student / persisted state
- [ ] deterministic MCQ evaluation
- [ ] free-text rubric evaluation
- [ ] understood/not-understood routing
- [ ] misconception-targeted remediation
- [ ] hint escalation
- [ ] deflection path
- [ ] Leak Guard pipeline
- [ ] formative feedback
- [ ] stage/progress state updates
- [ ] mastery service
- [ ] context sliding window + rolling summary
- [ ] session/message/feedback persistence
- [ ] code run/submit services
- [ ] SSE streaming after validation
- [ ] full tutor API
- [ ] progress API
- [ ] admin metrics/logs API
- [ ] end-to-end backend test for a complete problem journey

### Exit criteria
- A complete problem can be finished through the backend/API using deterministic MCQ grading and the LLM rubric path.
- Wrong answers loop through targeted guidance.
- Hint level escalates and persists.
- Student solution requests are deflected.
- Leak Guard blocks or regenerates unsafe tutor output.
- Learning progress is updated from real session events.
- Code execution is isolated from the API process.
- `openapi.json` is exported and becomes the frontend contract.

## Milestone 3 - Frontend + Seed Library + Evaluation + Documentation

### Goal
Build the browser experience around the proven API, add seed problems, automated pedagogical evaluation, and project documentation.

### Checklist
- [ ] React/Vite/Tailwind application shell
- [ ] auth pages
- [ ] protected routing
- [ ] dashboard
- [ ] problem library
- [ ] paste-problem flow
- [ ] three-panel tutor workspace
- [ ] persistent stage progress tracker
- [ ] MCQ card and hint interaction
- [ ] free-text chat with SSE
- [ ] Monaco editor
- [ ] code run/submit results
- [ ] feedback view
- [ ] profile settings / dark mode
- [ ] admin UI
- [ ] seed problem authoring format
- [ ] initial curated problem set
- [ ] offline plan generation/verifier runner
- [ ] evaluation YAML corpus
- [ ] DAVR/SRI/JDR harness
- [ ] regression suite for known failures
- [ ] Playwright smoke tests
- [ ] README/setup guide
- [ ] architecture/design docs
- [ ] test plan/results
- [ ] evaluation report template

### Exit criteria
- Fresh setup runs on Windows with documented prerequisites.
- A student can complete a problem end-to-end in the browser.
- Progress tracker reflects actual backend state.
- Code editor and execution work through the sandbox boundary.
- Verified/unverified plan state is visible when relevant.
- Evaluation harness produces reproducible metrics with run metadata.
- README and documentation reflect the implemented system, not aspirational features.

## Post-milestone stretch only
- pgvector + embeddings RAG over DSA notes
- additional sandbox languages
- spaced repetition
- deployment
