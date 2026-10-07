import os
import pytest

from backend.app.services.sandbox.base import (
    ExecutionRequest,
    ExecutionStatus,
)
from backend.app.services.sandbox.development_executor import (
    DevelopmentSubprocessSandbox,
)


@pytest.fixture
def sandbox():
    return DevelopmentSubprocessSandbox(timeout_seconds=2.0)


@pytest.mark.asyncio
async def test_sandbox_successful_execution(sandbox: DevelopmentSubprocessSandbox):
    code = "print('Hello, Socratic DSA Tutor!')"
    req = ExecutionRequest(code=code)
    result = await sandbox.execute(req)

    assert result.status == ExecutionStatus.SUCCESS
    assert "Hello, Socratic DSA Tutor!" in result.stdout
    assert result.exit_code == 0
    assert result.execution_time_ms > 0


@pytest.mark.asyncio
async def test_sandbox_with_stdin(sandbox: DevelopmentSubprocessSandbox):
    code = """
import sys
line = sys.stdin.read().strip()
print(f"Echo: {line}")
"""
    req = ExecutionRequest(code=code, stdin="DSA Test Input")
    result = await sandbox.execute(req)

    assert result.status == ExecutionStatus.SUCCESS
    assert "Echo: DSA Test Input" in result.stdout


@pytest.mark.asyncio
async def test_sandbox_syntax_error(sandbox: DevelopmentSubprocessSandbox):
    code = "def bad_syntax(:"
    req = ExecutionRequest(code=code)
    result = await sandbox.execute(req)

    assert result.status == ExecutionStatus.COMPILATION_ERROR
    assert result.exit_code != 0
    assert "SyntaxError" in result.stderr


@pytest.mark.asyncio
async def test_sandbox_runtime_error(sandbox: DevelopmentSubprocessSandbox):
    code = "1 / 0"
    req = ExecutionRequest(code=code)
    result = await sandbox.execute(req)

    assert result.status == ExecutionStatus.RUNTIME_ERROR
    assert result.exit_code != 0
    assert "ZeroDivisionError" in result.stderr


@pytest.mark.asyncio
async def test_sandbox_timeout(sandbox: DevelopmentSubprocessSandbox):
    code = """
import time
time.sleep(5)
"""
    # Set request timeout to 1.0s
    req = ExecutionRequest(code=code, timeout_seconds=1.0)
    result = await sandbox.execute(req)

    assert result.status == ExecutionStatus.TIME_LIMIT_EXCEEDED
    assert "timed out" in result.stderr.lower()


@pytest.mark.asyncio
async def test_sandbox_process_isolation(sandbox: DevelopmentSubprocessSandbox):
    code = """
import os
print(os.getpid())
"""
    req = ExecutionRequest(code=code)
    result = await sandbox.execute(req)

    assert result.status == ExecutionStatus.SUCCESS
    child_pid = int(result.stdout.strip())
    # The child PID must be different from current process PID
    assert child_pid != os.getpid()
