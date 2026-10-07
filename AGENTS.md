# Socratic DSA Tutor - Agent Control Rules

## Purpose
This repository is the implementation of the project:
**Socratic Pedagogy-Driven Large Language Model for Intelligent Formative Feedback in Education**.

The product scope is **DSA only**. The architecture and behavior in `SPEC.md` are the source of truth.

## Non-negotiable rules
1. Read `AGENTS.md`, `SPEC.md`, `PLAN.md`, `PROGRESS.md`, and `DECISIONS.md` before making changes.
2. Implement only the current milestone named by the active prompt in `prompts/`.
3. Do not redesign the architecture, rename core entities, change API contracts, or add unrelated features.
4. If a design change appears necessary, record the proposal in `DECISIONS.md` and stop before implementing it unless the active prompt explicitly authorizes the change.
5. Never expose hidden tutoring-plan answer keys to the browser.
6. Never send `correct_option_id` to the client.
7. Never run student code inside the FastAPI application process.
8. Never allow the student-facing tutor to output a complete solution, complete algorithm walkthrough, or full reference code.
9. All outgoing LLM-generated student-facing messages must pass the Leak Guard before they are returned or streamed.
10. The LangGraph workflow is the source of truth for tutoring state transitions. React must display state, not invent it.
11. LangGraph is part of the core workflow because it directly represents the supplied tutoring loop. LangChain is optional: use it only when it is genuinely useful for integration/helpers and does not change the locked architecture. Never add LangChain/LangGraph abstractions merely for technology-list compliance.
12. The database is the source of truth for persisted learning/session state.
13. Use typed Pydantic contracts and keep them backward compatible once established.
14. Keep prompts versioned under the backend prompt directory and treat prompt changes as code changes.
15. Write automated tests with each feature. Fix failing tests before moving to the next checklist item.
16. Do not start the next milestone after finishing the current one.
17. Do not claim a problem plan is verified unless its verification checks actually pass.
18. Preserve the terms and flow of the project diagrams and roadmap.
19. Do not add deployment work now; deployment is deferred.

## Working style
- Prefer small, composable services.
- Keep business rules out of route handlers when possible.
- Use dependency injection for database sessions and authenticated user context.
- Keep LLM calls behind a service boundary so models can be swapped through configuration.
- Keep sandbox execution behind a service boundary.
- Make failures explicit and observable through system logs.
- Never use real personal data in LLM prompts; use opaque user IDs in model-facing context.
- Use UTC timestamps in persistence.

## Required validation before declaring a milestone complete
- Run backend unit/integration tests relevant to the milestone.
- Run frontend type-check/lint/build when frontend code changed.
- Run the project smoke path defined in the active prompt.
- Update `PROGRESS.md` with completed work, tests, known issues, and the exact next milestone.
- List every created/modified file in the milestone summary.

## Git discipline
Create a git commit after each green milestone checkpoint. Commit messages should be descriptive and scoped.

## Scope boundary
The roadmap includes RAG/pgvector as a stretch goal. Do not implement RAG in the core milestones unless explicitly requested later.

The supplied diagrams and roadmap do not make MCP a core requirement. Do not add MCP to the architecture merely to mention it in a resume.
