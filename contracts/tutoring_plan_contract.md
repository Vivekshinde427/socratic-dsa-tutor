# Tutoring Plan Contract - Conceptual Schema

The implementation must produce a Pydantic-v2-validated structure equivalent to this contract.

```yaml
TutoringPlan:
  plan_version: string
  problem:
    title: string
    statement: string
    constraints: [string]
    examples: [Example]
    difficulty: easy|medium|hard
    topics: [string]
  pattern: string          # hidden
  prerequisites: [string]
  approaches:
    brute_force: Approach
    better: Approach|null
    optimal: Approach
  reference_solution:      # hidden
    language: python
    code: string
  brute_force_solution:    # hidden
    language: python
    code: string
  test_cases: [TestCase]    # hidden expected outputs
  socratic_steps: [Step]
  misconceptions: [Misconception]
  confidence: float
  verified: boolean
  verification_status: unverified|verified|verification_failed
  model_name: string
  prompt_version: string

Step:
  id: string
  stage: understand|examples_edges|brute_force|bottleneck|pattern_data_structure|algorithm_design|complexity|implementation|reflection
  question: string
  options: [MCQOption]
  correct_option_id: string # server-only
  option_feedback: [OptionFeedback] # server-only
  hint_ladder: [Hint]
  success_criteria: [string]

MCQOption:
  id: string
  text: string

OptionFeedback:
  option_id: string
  misconception_id: string|null
  why_wrong: string

Hint:
  level: 0|1|2|3|4
  content: string

Approach:
  idea: string
  time_complexity: string
  space_complexity: string
  why_it_works: string

Example:
  input: string
  output: string
  explanation: string

TestCase:
  input: string
  expected_output: string
  category: sample|edge|random|adversarial

Misconception:
  id: string
  description: string
  remediation_goal: string
```

## Client safety rule
The browser receives a sanitized step DTO with `question` and `options[{id,text}]` only, plus non-sensitive display metadata. Never send `correct_option_id`, reference code, brute-force code, hidden expected outputs, or full answer-key content.
