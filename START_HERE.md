# START HERE - Antigravity Execution Guide

## 1. Put this pack into the project repository
Copy the control-pack files into the root of your project repository. Keep the `diagrams/` folder as documentation/source reference.

## 2. Create the repo before coding
Initialize git and make an initial commit containing the control pack only.

## 3. Every Antigravity session starts the same way
Use the current milestone prompt and tell the agent:

> Read `AGENTS.md`, `SPEC.md`, `PLAN.md`, `PROGRESS.md`, and `DECISIONS.md` first. Inspect the current repository. Implement only the milestone in the supplied prompt. Preserve all locked contracts and architecture. Run tests, fix failures, update `PROGRESS.md`, list changed files, and stop at the milestone boundary.

## 4. Execute in three fresh sessions
- Session 1: `prompts/01_backend_foundation.md`
- Session 2: `prompts/02_tutoring_engine.md`
- Session 3: `prompts/03_frontend_evaluation.md`

Do not paste the entire project specification into every prompt manually; the files are the persistent memory.

## 5. After each session
Check:
- tests are green
- `PROGRESS.md` is truthful
- changed files make sense
- no contract drift
- git diff is understood

Then commit the milestone.

## 6. If the agent drifts
Stop the session. Do not let it continue into unrelated refactors. Revert to the last green commit, start a fresh session, and rerun the same milestone prompt.

## 7. If a locked design really must change
The agent must document the proposed change in `DECISIONS.md` before implementing it.

## 8. Important boundary
This pack defines the core project. RAG, pgvector, deployment, additional languages, and other stretch ideas come only after the three core milestones work end-to-end.
