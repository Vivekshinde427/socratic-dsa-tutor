# Antigravity Milestone 2 - Tutoring Engine + Complete Backend API

You are implementing Milestone 2 of the Socratic DSA Tutor.

## Before touching code
Read, in this order:
1. `AGENTS.md`
2. `SPEC.md`
3. `PLAN.md`
4. `PROGRESS.md`
5. `DECISIONS.md`
6. `contracts/tutoring_plan_contract.md`

Inspect the existing repository and tests. Preserve Milestone 1 behavior and contracts.

## Scope
Implement only Milestone 2:
- LangGraph tutoring state and graph
- context pipeline
- intent routing
- tutoring-step presentation
- human-in-the-loop/persisted student turn handling
- deterministic MCQ evaluation
- free-text evaluation rubric
- understood/not-understood routing
- targeted remediation
- hint ladder
- request-solution/jailbreak deflection
- Leak Guard
- formative feedback
- progress/mastery updates
- session/message/feedback persistence
- code run/submit boundary
- SSE for validated free-text tutor responses
- complete backend API
- admin/progress endpoints
- end-to-end backend test

Do not implement the final frontend, seed-library expansion, RAG, deployment, MCP, or unrelated capabilities.

## LangGraph behavior
Implement nodes named or clearly equivalent to the ones in `SPEC.md`:
- load_context
- route_intent
- get_or_create_plan
- present_step
- await_student
- evaluate
- further_guidance
- formative_feedback
- update_progress
- guard
- deflect path

Workflow must preserve the Diagram 1 semantics.

The graph/workflow engine decides state transitions. React/API clients do not decide whether a learner advances a stage.

## Stage progression
Use the canonical stages from the specification.

At each active step:
- show a guided question/MCQ
- accept student response
- evaluate it
- if understood, mark stage evidence and advance
- if not understood, identify/remediate the misconception and loop back for another attempt

Keep learner-visible progress derived from persisted stage state.

## MCQ rules
The server owns the answer key.

Client payload:
```json
{
  "question": "...",
  "options": [
    {"id": "A", "text": "..."},
    {"id": "B", "text": "..."},
    {"id": "C", "text": "..."},
    {"id": "D", "text": "..."}
  ]
}
```

Never include the correct answer ID in client responses.

Grade by exact server-side comparison.

## Free-text evaluation
Use the LLM only to produce structured evaluation against a rubric. Example output:
- classification
- confidence
- misconception_id
- evidence
- missing_concept

The graph routes based on this structured evaluation.

## Hint behavior
Persist hint level. Escalate one level for each explicit stuck request or repeated failure according to the stage policy.

Never give full code. Level 4 is the final permitted scaffold and must contain blanks/gaps.

## Leak Guard
Every LLM-generated learner-facing message must pass through:
1. regex/AST scan
2. normalized reference-solution similarity check
3. fixed cheap-judge rubric

On failure, regenerate up to two times, then return a safe fallback question.

Do not stream unvalidated output. Validate the complete response before emitting SSE content.

## Context
Implement the V1 Diagram 2 pipeline using:
- current query
- problem
- current stage
- recent 6-8 turns
- rolling summary
- progress/mastery
- profile/preferences as needed
- hints already used

Drop irrelevant/duplicate content. Update rolling summary periodically.

Do not add pgvector/RAG in this milestone.

## Code execution
Expose code run/submit APIs through a sandbox service. Never execute student code inside the FastAPI process.

Return structured results such as:
- status
- passed
- runtime_ms
- stdout/stderr
- failed_tests count/details appropriate for the UI

Do not reveal hidden expected outputs beyond what the product contract permits.

## Security
Protect endpoints with auth/roles. Requests for full solutions must be logged and deflected. Prompt-injection content is untrusted input.

## Required end-to-end test
Prove through API/graph tests that a synthetic student can:
1. start a problem
2. receive the first Socratic step
3. answer an MCQ correctly and advance
4. answer a later MCQ incorrectly
5. receive targeted remediation
6. use another attempt and advance
7. request a hint and see persisted hint escalation
8. request the full solution and receive a Socratic deflection
9. submit a code attempt through the sandbox boundary
10. finish the required conceptual stages
11. receive formative feedback
12. have learning progress updated

Also include Leak Guard regression cases.

## OpenAPI handoff
At the end of this milestone, generate a stable `openapi.json` from FastAPI and ensure the frontend can treat it as its API contract.

## Done conditions
- All Milestone 2 tests pass.
- End-to-end backend tutoring journey passes.
- Leak Guard regression cases pass.
- No secret answer keys appear in API JSON.
- No unvalidated LLM output is streamed.
- Progress is backed by persistent state.
- Update `PROGRESS.md`, list changed files, record known issues, and stop.
- Do not begin Milestone 3.
