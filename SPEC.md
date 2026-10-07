# Socratic DSA Tutor - Locked Implementation Specification

## 1. Product definition
A web-based DSA tutoring application in which a student selects or pastes a DSA problem and is guided through structured Socratic learning instead of being handed the solution.

The tutor uses adaptive questions, MCQs, contextual hints, response evaluation, formative feedback, code execution, and learning-progress tracking. The product focuses on conceptual understanding and independent problem solving.

Primary stack:
- Frontend: React + Vite + TypeScript + Tailwind
- State/API: Zustand + React Query (or TanStack Query) + React Router
- Code editor: Monaco
- Backend: Python 3.11+ + FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic
- LLM: Google Gemini through an isolated LLM service
- Orchestration: LangGraph + LangChain Google integration
- Database: PostgreSQL 16
- Code execution: sandbox service; Judge0 CE where practical, with a locked-down Python-only development fallback
- Streaming: Server-Sent Events for free-text tutor responses
- Testing: pytest + httpx + Playwright + custom evaluation harness

Deployment is deferred.

## 2. Source architecture
The supplied diagrams define the conceptual architecture:

### Diagram 1 / pedagogical loop
Student Query -> Context Understanding -> Generate Socratic Question/Hint -> Student Response -> Response Evaluation -> Concept Understood?
- No -> Further Guidance -> return to context
- Yes -> Formative Feedback -> Update Learning Progress

### Diagram 2 / context pipeline
Context Sources:
- Current Query
- Conversation History
- Previous Responses
- Learning Progress
- User Profile

Processing:
- Retrieve relevant information
- Filter irrelevant content
- Summarize and structure context

Representation:
- Structured Context
- Vector/Embedding is a later extension, not core V1

Usage:
- Provide context to LLM for relevant response generation

Update:
- New interaction data updates the context state

### Diagram 3 / system tiers
1. Student Interface
2. Application Backend
3. LLM Service
4. Database
5. Deployment & Infrastructure

The implementation must preserve this separation.

## 3. Core accuracy architecture
The central reliability rule is:

**LLM generates and explains. Code execution verifies. Database remembers. Server grades.**

The system uses a hidden Problem Analyst to generate a structured Tutoring Plan. The student-facing Tutor reads the plan but does not expose the hidden answer key.

Every generated plan must have a verification status. A plan may be `verified`, `unverified`, or `verification_failed` depending on actual checks.

## 4. Hidden tutoring plan
A problem plan contains:
- normalized problem statement
- constraints
- examples
- difficulty
- topics
- hidden key pattern
- prerequisites
- brute-force approach
- better approach when applicable
- optimal approach
- time and space complexity for each approach
- why each approach works
- hidden reference solution
- hidden brute-force solution
- generated test cases and expected outputs
- ordered Socratic steps
- misconceptions catalog
- confidence
- verification metadata
- model/prompt version

Plans are generated once per problem when possible, cached in PostgreSQL, and reused across students.

## 5. Socratic stages
The canonical stages are:
1. Understand
2. Examples and Edge Cases
3. Brute Force
4. Bottleneck
5. Pattern and Data Structure
6. Algorithm Design and Invariant
7. Complexity: Time and Space
8. Implementation
9. Reflection

Easy problems may merge stages. The plan generator decides the appropriate stage count.

For the learner-facing UI, a problem journey may be displayed as:
- LOCKED
- ACTIVE
- UNDER_REVIEW
- COMPLETED
- NEEDS_REVISIT

The progress bar is evidence-based, not a timer or artificial percentage counter. A stage advances only when the evaluation rules determine that the learner has demonstrated sufficient understanding.

## 6. Learning journey semantics
The intended pedagogy is discovery of:

Problem -> understanding -> example reasoning -> brute force -> bottleneck -> data structure/pattern -> better/optimal algorithm -> complexity -> implementation -> testing -> reflection.

The tutor may explicitly affirm or correct the student's approach, but should preserve the discovery process.

Example behavior:
- Valid brute force: affirm it and ask about complexity.
- Good direction but incomplete: identify what is missing and ask one targeted question.
- Wrong idea: state that it does not address the current bottleneck, explain only what is necessary, and ask the next targeted question.
- Student says "I'm stuck": escalate one hint level.

Do not reveal the hidden optimal approach before the learner reaches the appropriate stage.

## 7. MCQ contract
Each Socratic step can contain:
- stage
- question
- four answer options
- hidden correct option ID
- per-option misconception ID
- per-option explanation / why wrong
- hint ladder

The client payload contains only:
- question
- options[{id, text}]

The correct option ID stays on the server.

MCQ grading is deterministic: compare the selected option ID against the stored correct option ID. Do not use an LLM to decide whether an MCQ option is correct.

## 8. Hint ladder
Hint levels:
- Level 0: only the Socratic question
- Level 1: conceptual nudge
- Level 2: names the pattern or data-structure family without explaining application
- Level 3: plain-language approach outline with one gap left for the learner
- Level 4: pseudocode skeleton with blanks; never complete code

Wrong answers or "I'm stuck" escalate guidance. Repeated hints are stored for learning analytics.

## 9. Student free-text evaluation
Free-text student responses are classified into structured outcomes such as:
- correct
- partially_correct
- misconception
- incorrect
- stuck
- irrelevant
- request_solution
- off_topic

The LLM may perform the rubric judgment, but the workflow engine decides routing.

## 10. LangGraph state
Core state includes:
- user_id
- session_id
- problem_id
- plan
- step_index
- hint_level
- attempts
- mastery
- memory_window
- rolling_summary
- hints_already_given
- last_student_input
- evaluation
- response
- current_stage_status

Core nodes:
1. load_context
2. route_intent
3. get_or_create_plan
4. present_step
5. await_student
6. evaluate
7. conditional understood?
8. further_guidance
9. formative_feedback
10. update_progress
11. guard

Requests for a full solution or jailbreak/override attempts go through a deflection path.

## 11. Context management
V1 context uses:
- current query
- current problem
- current stage
- recent conversation window (approximately last 6-8 turns)
- rolling summary
- previous responses
- learning progress
- user profile/preferences where appropriate
- hints already given

The system removes irrelevant greetings/duplicates and updates the rolling summary periodically.

RAG/pgvector/embeddings are stretch work after the core tutoring engine is stable.

## 12. Leak Guard
Every student-facing LLM response is checked before release.

Checks, cheapest first:
1. Pattern/regex and AST inspection for code and overly complete pseudocode.
2. Similarity against hidden reference solution using normalized tokens.
3. Cheap LLM judge against a fixed leak rubric.

On failure:
- regenerate, up to two attempts
- then use a safe fallback Socratic question

Every guard event is logged.

The Guard must detect, among other things:
- full solution code
- complete algorithm walkthrough before the student reaches it
- premature final complexity
- hidden answer-key content

Unvalidated streaming is forbidden. Validate before SSE chunks are exposed to the browser.

## 13. Verification pipeline
For a generated plan:
1. Validate structured output against Pydantic.
2. Generate or obtain brute-force and reference solutions.
3. Generate edge cases and normal cases.
4. Run both solutions in a sandbox.
5. Compare outputs.
6. Reject or mark unverified when they disagree or the execution is invalid.
7. Perform an MCQ blind-solve check using a separate model call without the answer key.
8. Review complexity claims for known curated benchmark problems where available.

Only actually passing plans are marked verified.

## 14. Code execution
Student code must never execute in the API process.

The execution boundary must support:
- execution timeout
- CPU limit
- memory limit
- no network
- bounded code and input sizes
- isolated temporary filesystem/container where applicable

Core development may start with Python. Multi-language support may be added only when the sandbox is stable.

## 15. Mastery tracking
Per user and topic, keep mastery in [0, 1].

A simple explainable update is preferred:
- correct first try -> larger increase
- correct after hints -> smaller increase based on hint level
- wrong -> small decrease
- slight time-based decay

This is explicitly not a research-grade knowledge-tracing model.

## 16. Completion
A session/problem is conceptually complete when required conceptual stages are completed.

A full implementation completion additionally requires:
- complexity understood
- code stage completed when selected
- required tests passing
- reflection completed

The UI must distinguish conceptual completion from implementation/test completion where necessary.

## 17. Database entities
Required tables:
- users
- conversations
- sessions
- messages
- feedback
- learning_progress
- system_logs
- problems
- problem_plans
- mcq_attempts
- code_runs
- eval_runs
- eval_results

Use Alembic from the beginning. Index messages by session/time and learning progress by user/topic.

## 18. API surface
Auth:
- POST /auth/register
- POST /auth/login
- POST /auth/refresh
- POST /auth/logout
- GET /auth/me

Profile:
- GET /users/me
- PUT /users/me

Problems:
- GET /problems
- GET /problems/{id}
- POST /problems/paste

Sessions:
- POST /sessions
- GET /sessions
- GET /sessions/{id}
- GET /sessions/{id}/messages

Tutor:
- POST /sessions/{id}/answer
- POST /sessions/{id}/message
- POST /sessions/{id}/hint
- POST /sessions/{id}/code/run
- POST /sessions/{id}/code/submit

Progress:
- GET /progress/me
- GET /progress/recommendations

Admin:
- GET /admin/users
- PATCH /admin/users/{id}
- GET /admin/metrics
- GET /admin/logs
- POST /admin/problems/{id}/regenerate-plan

## 19. Frontend screens
1. Login / Register
2. Dashboard
3. Problem Library
4. Tutor Workspace
5. Feedback View
6. Profile Settings
7. Admin

Tutor Workspace:
- Left: problem statement and examples
- Center: Socratic chat, MCQ card, Submit, I'm stuck, hint indicator, free-text input
- Right: Monaco editor, language selector, Run/Submit, test results

The progress tracker remains visible throughout the tutoring session.

## 20. Security
- Password hashing with argon2 or bcrypt.
- Short-lived JWT access tokens.
- Refresh token in httpOnly cookie.
- Restricted CORS.
- Rate limits on auth/tutor endpoints.
- Request size limits for problem text and code.
- Student code isolated from the API process.
- Prompt-injection defense by treating student/pasted content as untrusted data.
- Hidden MCQ keys never sent to browser.
- Admin routes role-protected.
- Avoid personal data in LLM prompts and logs.
- UI includes concise privacy and academic-integrity notice.

## 21. Evaluation
The system should support:
- plan verification pass rate
- MCQ blind-solve mismatch detection
- MCQ manual review rubric
- complexity accuracy benchmark
- DAVR = direct-answer violations / evaluated turns * 100
- SRI = Socratic-structured responses / evaluated turns * 100
- JDR = successfully deflected adversarial attempts / adversarial attempts * 100

Targets are internal engineering goals, not pre-claimed results:
- DAVR <= 2%
- SRI >= 90%
- JDR >= 95%

Evaluation records must include model name, temperature, prompt version and run metadata.

## 22. Problem sources
Do not scrape LeetCode or other platforms.

Supported sources:
1. User-pasted problem statement.
2. Seed library of independently authored problems in the team's own words.
3. Offline pre-generation and verification for seed plans.

## 23. Repository intent
The repository is organized so the backend tutoring engine can be proven before the frontend is built around it.

The active milestone prompt is the authority for what may be changed at that time.
