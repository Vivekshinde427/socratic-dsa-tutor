# Antigravity Milestone 3 - Frontend + Seed Library + Evaluation + Documentation

You are implementing Milestone 3 of the Socratic DSA Tutor.

## Before touching code
Read, in this order:
1. `AGENTS.md`
2. `SPEC.md`
3. `PLAN.md`
4. `PROGRESS.md`
5. `DECISIONS.md`
6. `contracts/tutoring_plan_contract.md`
7. the generated `openapi.json`

Inspect all existing backend tests and endpoints. Do not break Milestones 1 or 2.

## Scope
Implement only Milestone 3:
- React/Vite/TypeScript/Tailwind application
- authentication pages and protected routing
- dashboard
- problem library
- paste problem flow
- tutor workspace
- stage-based progress tracker
- MCQ and hints
- free-text SSE chat
- Monaco editor
- code run/submit results
- completion/feedback view
- profile settings/dark mode
- admin pages
- seed-problem authoring format and initial curated set
- offline plan generation/verification scripts
- evaluation corpus and metrics harness
- regression tests
- Playwright smoke tests
- README and project documentation

Do not add RAG, deployment, MCP, or unrelated product features.

## Frontend requirements
Use:
- React
- Vite
- TypeScript
- Tailwind
- React Router
- Zustand for client state where useful
- React Query/TanStack Query for server state
- Monaco editor

The UI should be clean, responsive, and focused on learning.

## Tutor workspace layout
Three panels:
- Left: problem statement and examples
- Center: Socratic tutor conversation, MCQ, Submit, I'm stuck, hint indicator, free-text
- Right: Monaco editor, language selection, Run/Submit, test results

Keep the progress tracker visible beside or above the workspace. It must display actual backend state.

## Progress tracker
Show the learner journey through canonical stages. Use clear states such as:
- locked
- active
- under review
- completed
- needs revisit

For completed work, provide immediate status feedback such as:
- correct
- partially correct
- needs another attempt
- stage completed

Do not compute fake progress locally.

## Problem completion UX
At the end, show:
- stage completion summary
- strengths
- gaps
- complexity summary when unlocked
- implementation/test result when applicable
- transferable/general lesson
- similar-problem suggestions when the API provides them

Distinguish conceptual completion from full implementation/test completion.

## Problem library
Create an initial library of independently authored DSA problems in the project's own wording. Do not scrape LeetCode or other sites.

Cover the major DSA families listed in `SPEC.md`.

The seed-problem format must support offline plan generation and verification.

## Evaluation harness
Implement the YAML-driven evaluation corpus described by `SPEC.md`.

Include representative cases for:
- direct solution requests
- override/jailbreak attempts
- misconceptions
- vague/stuck responses

Compute and report:
- DAVR
- SRI
- JDR

Store prompt/model/config metadata with each run. Add regression tests for failures discovered during development.

Do not fabricate evaluation results. The report must distinguish actual measured values from internal targets.

## Documentation
Update or create:
- README
- architecture/design document
- API usage/reference notes
- test plan/results
- evaluation report template/results
- user manual notes/screenshots guidance

Documentation must describe implemented behavior only.

## Windows setup
Provide PowerShell-friendly commands and prerequisites. Document Docker Desktop/WSL2 only where required by the sandbox/database path actually implemented.

## Required browser smoke test
Use Playwright to prove at least:
1. register/login
2. open problem library
3. start tutoring session
4. receive a Socratic step
5. select an MCQ
6. see actual progress-stage update
7. use a hint
8. interact with Monaco/run code
9. reach the feedback/completion view for a test problem

## Done conditions
- Frontend typecheck/lint/build pass.
- Backend regression suite remains green.
- Playwright smoke path passes.
- Evaluation harness produces reproducible output format.
- README can guide a clean Windows setup.
- Update `PROGRESS.md` to Milestone 3 complete, list known limitations and stretch goals.
- Stop. Do not start post-milestone stretch work.
