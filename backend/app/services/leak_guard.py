"""
Leak Guard: ensures no LLM-generated student-facing response leaks
the hidden answer key, complete solutions, or premature algorithm details.

Pipeline (cheapest first):
1. Regex/AST pattern scan for code and overly complete pseudocode
2. Normalized token similarity against hidden reference solution
3. Cheap LLM judge against fixed leak rubric

On failure: regenerate up to 2 times, then safe fallback.
"""
import ast
import json
import re
from typing import Optional

from backend.app.core.logging import logger
from backend.app.services.llm.gemini_service import GeminiService, gemini_service
from backend.app.services.prompts.tutor_prompts import (
    LEAK_GUARD_SYSTEM_PROMPT,
    LEAK_GUARD_USER_TEMPLATE,
)


class LeakGuardResult:
    def __init__(self, safe: bool, reason: str = "", check_level: str = ""):
        self.safe = safe
        self.reason = reason
        self.check_level = check_level


class LeakGuard:
    """Guard pipeline that validates tutor responses before student exposure."""

    # Patterns indicating likely complete code
    CODE_PATTERNS = [
        r"def\s+\w+\s*\([^)]*\)\s*:",         # Python function definition
        r"for\s+\w+\s+in\s+",                  # for loop
        r"while\s+.*:",                          # while loop
        r"if\s+.*:",                             # if statement
        r"elif\s+.*:",                           # elif statement
        r"class\s+\w+.*:",                       # class definition
        r"return\s+.+",                          # return statement
        r"import\s+\w+",                         # import
        r"\w+\s*=\s*.+",                         # variable assignment
    ]

    # Threshold: if response has more than this many code-like lines without blanks, flag it
    MAX_CODE_LINES = 2

    # Similarity threshold for reference comparison
    SIMILARITY_THRESHOLD = 0.6

    def __init__(self, llm: Optional[GeminiService] = None):
        self.llm = llm or gemini_service

    def _check_regex_ast(self, response: str) -> LeakGuardResult:
        """Check 1: Pattern/regex and AST inspection for code leaks."""
        # If the response contains scaffold blanks, it's explicitly designed as a scaffold
        has_blanks = "___" in response or "<TODO>" in response

        lines = response.strip().split("\n")

        # Count lines that look like executable code
        code_line_count = 0
        code_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("//"):
                continue
            for pattern in self.CODE_PATTERNS:
                if re.search(pattern, stripped):
                    code_line_count += 1
                    code_lines.append(stripped)
                    break

        if not has_blanks and code_line_count > self.MAX_CODE_LINES:
            return LeakGuardResult(
                safe=False,
                reason=f"Response contains {code_line_count} code-like lines (max {self.MAX_CODE_LINES})",
                check_level="regex_ast",
            )

        # Try to parse code lines as Python AST
        if code_lines and not has_blanks:
            candidate_code = "\n".join(code_lines)
            try:
                tree = ast.parse(candidate_code)
                executable = [
                    n for n in ast.walk(tree)
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.For, ast.While, ast.If, ast.Return, ast.Assign))
                ]
                if len(executable) > 2:
                    return LeakGuardResult(
                        safe=False,
                        reason=f"Response parses as Python code with {len(executable)} executable statements",
                        check_level="regex_ast",
                    )
            except SyntaxError:
                pass

        return LeakGuardResult(safe=True, check_level="regex_ast")

    def _normalize_tokens(self, text: str) -> set:
        """Normalize text to a set of lowercase alphanumeric tokens."""
        return set(re.findall(r"[a-z0-9_]+", text.lower()))

    def _check_similarity(
        self, response: str, reference_code: str
    ) -> LeakGuardResult:
        """Check 2: Normalized token similarity against hidden reference solution."""
        if not reference_code:
            return LeakGuardResult(safe=True, check_level="similarity")

        resp_tokens = self._normalize_tokens(response)
        ref_tokens = self._normalize_tokens(reference_code)

        if not ref_tokens:
            return LeakGuardResult(safe=True, check_level="similarity")

        # Jaccard-like similarity: what fraction of reference tokens appear in response
        overlap = resp_tokens & ref_tokens
        similarity = len(overlap) / len(ref_tokens) if ref_tokens else 0.0

        if similarity > self.SIMILARITY_THRESHOLD:
            return LeakGuardResult(
                safe=False,
                reason=f"Response has {similarity:.1%} token overlap with reference solution (threshold: {self.SIMILARITY_THRESHOLD:.0%})",
                check_level="similarity",
            )

        return LeakGuardResult(safe=True, check_level="similarity")

    async def _check_llm_judge(
        self, response: str, problem_title: str, current_stage: str
    ) -> LeakGuardResult:
        """Check 3: Cheap LLM judge against fixed leak rubric."""
        try:
            prompt = LEAK_GUARD_USER_TEMPLATE.format(
                response=response,
                problem_title=problem_title,
                current_stage=current_stage,
            )
            raw = await self.llm.generate_text(
                prompt=prompt,
                system_instruction=LEAK_GUARD_SYSTEM_PROMPT,
                temperature=0.0,
            )
            # Parse the JSON response
            cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
            cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
            result = json.loads(cleaned)
            is_safe = result.get("safe", True)
            reason = result.get("reason", "")
            return LeakGuardResult(
                safe=is_safe,
                reason=reason,
                check_level="llm_judge",
            )
        except Exception as e:
            logger.warning(f"Leak Guard LLM judge failed: {e}. Defaulting to safe.")
            # On LLM failure, allow through (fail-open for judge only,
            # regex/similarity already ran)
            return LeakGuardResult(safe=True, reason=f"Judge error: {e}", check_level="llm_judge")

    async def check(
        self,
        response: str,
        reference_code: str = "",
        problem_title: str = "",
        current_stage: str = "",
    ) -> LeakGuardResult:
        """Run the full leak guard pipeline, cheapest checks first."""

        # Check 1: Regex/AST
        result = self._check_regex_ast(response)
        if not result.safe:
            logger.warning(f"Leak Guard BLOCKED (regex/ast): {result.reason}")
            return result

        # Check 2: Similarity
        result = self._check_similarity(response, reference_code)
        if not result.safe:
            logger.warning(f"Leak Guard BLOCKED (similarity): {result.reason}")
            return result

        # Check 3: LLM judge (only if LLM key is configured)
        if self.llm.api_key:
            result = await self._check_llm_judge(response, problem_title, current_stage)
            if not result.safe:
                logger.warning(f"Leak Guard BLOCKED (llm_judge): {result.reason}")
                return result

        return LeakGuardResult(safe=True, check_level="all_passed")


# Default singleton
leak_guard = LeakGuard()
