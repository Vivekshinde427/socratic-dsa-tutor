# Socratic DSA Tutor - Architecture Decisions

## AD-001 - Follow supplied diagrams and roadmap
Status: LOCKED
Decision: The supplied diagrams and roadmap are the source of truth for architecture, workflow, scope, and terminology.

## AD-002 - DSA-only scope
Status: LOCKED
Decision: The application focuses on Data Structures and Algorithms. Do not expand to other academic subjects in this implementation.

## AD-003 - Accuracy-first architecture
Status: LOCKED
Decision: Separate hidden Problem Analyst/answer key from the student-facing Tutor; verify plans before teaching; deterministic MCQ grading; Leak Guard on LLM-generated student-facing output.

## AD-004 - Context V1
Status: LOCKED
Decision: Use bounded recent-turn context plus rolling summaries. Vector/RAG is stretch work.

## AD-005 - Deployment
Status: DEFERRED
Decision: Do not spend core milestones on production deployment.

## AD-006 - Code execution
Status: LOCKED
Decision: Student code never runs in the FastAPI process. Use a sandbox boundary with resource/time/network controls.

## AD-007 - MCP
Status: NOT CORE
Decision: MCP is not part of the supplied architecture/roadmap and will not be added merely as resume decoration. Revisit only through an explicit architecture decision later.

## AD-007A - LangGraph / LangChain usage
Status: LOCKED
Decision: LangGraph is used where it directly implements the supplied Diagram 1 tutoring state graph. LangChain is optional and must be used only where it provides useful integration/helpers without changing the locked architecture, contracts, or workflow. Never introduce either library merely to satisfy a technology checklist.

## AD-008 - Progress tracking
Status: LOCKED
Decision: The learner-visible progress tracker represents actual stage state/evidence from the backend, not a frontend-only percentage counter.

## AD-009 - Problem sources
Status: LOCKED
Decision: No scraping of LeetCode or similar platforms. Use user-pasted problems and an independently authored seed library.

## AD-010 - Change protocol
Any proposed change to a locked decision must be written here with rationale, impact, migration/test plan, and approval status before code changes are made.
