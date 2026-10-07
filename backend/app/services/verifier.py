import ast
import json
import textwrap
from typing import Any, List, Optional
from pydantic import BaseModel

from backend.app.core.logging import logger
from backend.app.schemas.tutoring_plan import (
    TutoringPlan,
    VerificationStatus,
    TestCase,
)
from backend.app.services.sandbox.base import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    SandboxInterface,
)
from backend.app.services.sandbox.development_executor import (
    development_sandbox,
)


class TestCaseVerificationResult(BaseModel):
    test_case_index: int
    test_input: str
    expected_output: str
    reference_output: Optional[str] = None
    brute_force_output: Optional[str] = None
    passed: bool
    error: Optional[str] = None


class VerificationResult(BaseModel):
    verified: bool
    status: VerificationStatus
    notes: str
    test_results: List[TestCaseVerificationResult] = []


HARNESS_TEMPLATE = """
import sys
import json
import inspect

__CODE__

def _parse_input(raw_input):
    # Try JSON array / tuple parsing
    try:
        data = json.loads(f"[{raw_input}]")
        if isinstance(data, list):
            return tuple(data)
    except Exception:
        pass
    # Fallback to single string or raw argument
    try:
        return (json.loads(raw_input),)
    except Exception:
        return (raw_input,)

def _find_target():
    # 1. Look for 'solve'
    if 'solve' in globals() and callable(globals()['solve']):
        return globals()['solve']
    
    # 2. Look for class Solution
    if 'Solution' in globals() and inspect.isclass(globals()['Solution']):
        inst = globals()['Solution']()
        methods = [m for m in dir(inst) if not m.startswith('_') and callable(getattr(inst, m))]
        if methods:
            return getattr(inst, methods[0])
            
    # 3. Look for any custom defined function in globals
    for name, val in list(globals().items()):
        if not name.startswith('_') and callable(val) and name not in ['_parse_input', '_find_target', 'json', 'sys', 'inspect']:
            return val
    raise ValueError("No callable entry point function found in solution code.")

def _main():
    raw_input = __TEST_INPUT_REPR__
    func = _find_target()
    args = _parse_input(raw_input)
    try:
        res = func(*args)
    except TypeError:
        # If single argument expected
        res = func(args)
    
    # Print canonical JSON output
    print(json.dumps(res, sort_keys=True))

if __name__ == '__main__':
    _main()
"""


class PlanVerifier:
    def __init__(self, sandbox: Optional[SandboxInterface] = None):
        self.sandbox = sandbox or development_sandbox

    def _build_test_script(self, code: str, raw_input: str) -> str:
        return (
            HARNESS_TEMPLATE
            .replace("__CODE__", code)
            .replace("__TEST_INPUT_REPR__", repr(raw_input))
        )

    async def _run_solution_on_test(
        self, code: str, test_case: TestCase
    ) -> ExecutionResult:
        script = self._build_test_script(code, test_case.input)
        req = ExecutionRequest(
            language="python",
            code=script,
            timeout_seconds=4.0,
        )
        return await self.sandbox.execute(req)

    def _normalize_json_output(self, raw_stdout: str) -> Any:
        stripped = raw_stdout.strip()
        if not stripped:
            return None
        # Get last non-empty line
        last_line = stripped.splitlines()[-1]
        try:
            return json.loads(last_line)
        except Exception:
            return last_line

    async def verify_plan(self, plan: TutoringPlan) -> VerificationResult:
        logger.info(f"Starting verification for plan of '{plan.problem.title}'")

        if not plan.test_cases:
            return VerificationResult(
                verified=False,
                status=VerificationStatus.verification_failed,
                notes="Verification failed: Plan does not contain any test cases to execute.",
            )

        test_results: List[TestCaseVerificationResult] = []
        all_passed = True
        failure_reasons = []

        for idx, tc in enumerate(plan.test_cases):
            # 1. Run reference solution
            ref_exec = await self._run_solution_on_test(
                plan.reference_solution.code, tc
            )
            if ref_exec.status != ExecutionStatus.SUCCESS:
                all_passed = False
                err_msg = (
                    f"Reference solution failed on test case {idx + 1} ({tc.input}): "
                    f"{ref_exec.status.value} - {ref_exec.stderr.strip()}"
                )
                failure_reasons.append(err_msg)
                test_results.append(
                    TestCaseVerificationResult(
                        test_case_index=idx,
                        test_input=tc.input,
                        expected_output=tc.expected_output,
                        reference_output=ref_exec.stdout.strip(),
                        passed=False,
                        error=err_msg,
                    )
                )
                continue

            ref_val = self._normalize_json_output(ref_exec.stdout)

            # 2. Run brute force solution
            bf_exec = await self._run_solution_on_test(
                plan.brute_force_solution.code, tc
            )
            if bf_exec.status != ExecutionStatus.SUCCESS:
                all_passed = False
                err_msg = (
                    f"Brute-force solution failed on test case {idx + 1} ({tc.input}): "
                    f"{bf_exec.status.value} - {bf_exec.stderr.strip()}"
                )
                failure_reasons.append(err_msg)
                test_results.append(
                    TestCaseVerificationResult(
                        test_case_index=idx,
                        test_input=tc.input,
                        expected_output=tc.expected_output,
                        reference_output=str(ref_val),
                        brute_force_output=bf_exec.stdout.strip(),
                        passed=False,
                        error=err_msg,
                    )
                )
                continue

            bf_val = self._normalize_json_output(bf_exec.stdout)

            # 3. Compare outputs with expected output and with each other
            expected_val = self._normalize_json_output(tc.expected_output)

            # Standard comparison: allow list sorting if both are lists of unordered indices,
            # or exact match
            ref_matches_expected = (ref_val == expected_val) or (
                isinstance(ref_val, list)
                and isinstance(expected_val, list)
                and sorted(ref_val) == sorted(expected_val)
            )
            bf_matches_expected = (bf_val == expected_val) or (
                isinstance(bf_val, list)
                and isinstance(expected_val, list)
                and sorted(bf_val) == sorted(expected_val)
            )
            ref_matches_bf = (ref_val == bf_val) or (
                isinstance(ref_val, list)
                and isinstance(bf_val, list)
                and sorted(ref_val) == sorted(bf_val)
            )

            tc_passed = ref_matches_expected and bf_matches_expected and ref_matches_bf
            if not tc_passed:
                all_passed = False
                err_msg = (
                    f"Output mismatch on test case {idx + 1} ({tc.input}): "
                    f"expected={expected_val}, ref={ref_val}, brute_force={bf_val}"
                )
                failure_reasons.append(err_msg)
                test_results.append(
                    TestCaseVerificationResult(
                        test_case_index=idx,
                        test_input=tc.input,
                        expected_output=tc.expected_output,
                        reference_output=json.dumps(ref_val),
                        brute_force_output=json.dumps(bf_val),
                        passed=False,
                        error=err_msg,
                    )
                )
            else:
                test_results.append(
                    TestCaseVerificationResult(
                        test_case_index=idx,
                        test_input=tc.input,
                        expected_output=tc.expected_output,
                        reference_output=json.dumps(ref_val),
                        brute_force_output=json.dumps(bf_val),
                        passed=True,
                    )
                )

        if all_passed:
            notes = f"All {len(plan.test_cases)} test cases passed successfully for both reference and brute-force solutions."
            plan.verified = True
            plan.verification_status = VerificationStatus.verified
            plan.verification_notes = notes
            return VerificationResult(
                verified=True,
                status=VerificationStatus.verified,
                notes=notes,
                test_results=test_results,
            )
        else:
            notes = "Verification failed: " + "; ".join(failure_reasons)
            plan.verified = False
            plan.verification_status = VerificationStatus.verification_failed
            plan.verification_notes = notes
            return VerificationResult(
                verified=False,
                status=VerificationStatus.verification_failed,
                notes=notes,
                test_results=test_results,
            )


# Default verifier instance
plan_verifier = PlanVerifier()
