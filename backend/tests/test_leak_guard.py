"""
Leak Guard Regression Tests (Milestone 2, SPEC §12).
Verifies:
- Complete code solutions are blocked by regex/AST inspection
- Overly complete implementations are blocked
- Token overlap with hidden reference solution is blocked
- Socratic guided questions and nudges are permitted
- Scaffolds with blanks are permitted
"""
import pytest
from backend.app.services.leak_guard import LeakGuard, leak_guard


@pytest.mark.asyncio
async def test_leak_guard_blocks_full_python_solution():
    guard = LeakGuard()
    leaky_response = """
def twoSum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []
"""
    result = await guard.check(response=leaky_response, reference_code="")
    assert result.safe is False
    assert result.check_level == "regex_ast"
    assert "code-like lines" in result.reason or "executable statements" in result.reason


@pytest.mark.asyncio
async def test_leak_guard_blocks_multiline_code_block():
    guard = LeakGuard()
    leaky_response = """
Here is the code:
for i in range(len(nums)):
    for j in range(i + 1, len(nums)):
        if nums[i] + nums[j] == target:
            return [i, j]
"""
    result = await guard.check(response=leaky_response, reference_code="")
    assert result.safe is False
    assert result.check_level == "regex_ast"


@pytest.mark.asyncio
async def test_leak_guard_blocks_reference_solution_similarity():
    guard = LeakGuard()
    ref_code = "seen = {}; complement = target - num; return [seen[complement], i]"
    leaky_explanation = (
        "You should compute complement = target - num and look up if complement is in seen. "
        "Then return [seen[complement], i]."
    )
    result = await guard.check(response=leaky_explanation, reference_code=ref_code)
    assert result.safe is False
    assert result.check_level == "similarity"
    assert "overlap" in result.reason


@pytest.mark.asyncio
async def test_leak_guard_allows_socratic_questions():
    guard = LeakGuard()
    safe_response = (
        "Great observation! When looking at an element x, what value would you need to add to x "
        "to reach the target? Can we look up that needed value in O(1) time?"
    )
    result = await guard.check(
        response=safe_response,
        reference_code="def twoSum(nums, target): return []",
    )
    assert result.safe is True


@pytest.mark.asyncio
async def test_leak_guard_allows_scaffold_with_blanks():
    guard = LeakGuard()
    safe_scaffold = (
        "Consider this skeleton:\n"
        "for x in items:\n"
        "    if ___ in seen:\n"
        "        return [___, x]"
    )
    result = await guard.check(
        response=safe_scaffold,
        reference_code="def twoSum(nums, target): return []",
    )
    assert result.safe is True


@pytest.mark.asyncio
async def test_leak_guard_allows_conceptual_hint():
    guard = LeakGuard()
    safe_hint = "Think about trading space for time: what data structure provides O(1) average lookup?"
    result = await guard.check(response=safe_hint, reference_code="")
    assert result.safe is True
