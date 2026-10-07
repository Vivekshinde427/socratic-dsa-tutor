import asyncio
import os
import subprocess
import sys
import tempfile
import time
from typing import Optional

from backend.app.config import settings
from backend.app.core.logging import logger
from backend.app.services.sandbox.base import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    SandboxInterface,
)

MAX_OUTPUT_BYTES = 64 * 1024  # 64 KB limit


class DevelopmentSubprocessSandbox(SandboxInterface):
    """
    Subprocess-based sandbox for local development on Windows and other OS.
    Executes Python scripts in an isolated child process outside the FastAPI server process.
    Enforces time limits, output limits, and process isolation.
    """

    def __init__(self, timeout_seconds: Optional[float] = None):
        self.default_timeout = timeout_seconds or settings.SANDBOX_TIMEOUT_SECONDS

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        if request.language.lower() != "python":
            return ExecutionResult(
                status=ExecutionStatus.COMPILATION_ERROR,
                stdout="",
                stderr=f"Language '{request.language}' is not supported in the development sandbox.",
                exit_code=1,
                execution_time_ms=0.0,
            )

        timeout = request.timeout_seconds or self.default_timeout

        # Write to a temporary file
        temp_fd, temp_path = tempfile.mkstemp(suffix=".py", prefix="socratic_sandbox_")
        try:
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                f.write(request.code)

            start_time = time.time()

            def run_child():
                # Runs python in isolated child process with unbuffered binary stdio
                cmd = [sys.executable, "-I", temp_path]
                return subprocess.run(
                    cmd,
                    input=request.stdin.encode("utf-8") if request.stdin else b"",
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=timeout,
                )

            try:
                proc = await asyncio.to_thread(run_child)
                duration_ms = (time.time() - start_time) * 1000

                stdout_str = proc.stdout[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")
                stderr_str = proc.stderr[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")

                if proc.returncode == 0:
                    status = ExecutionStatus.SUCCESS
                else:
                    if "SyntaxError" in stderr_str or "IndentationError" in stderr_str:
                        status = ExecutionStatus.COMPILATION_ERROR
                    else:
                        status = ExecutionStatus.RUNTIME_ERROR

                return ExecutionResult(
                    status=status,
                    stdout=stdout_str,
                    stderr=stderr_str,
                    exit_code=proc.returncode,
                    execution_time_ms=duration_ms,
                )

            except subprocess.TimeoutExpired as te:
                duration_ms = (time.time() - start_time) * 1000
                stdout_str = (te.stdout or b"")[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")
                stderr_str = "Execution timed out (Time Limit Exceeded)"
                return ExecutionResult(
                    status=ExecutionStatus.TIME_LIMIT_EXCEEDED,
                    stdout=stdout_str,
                    stderr=stderr_str,
                    exit_code=-1,
                    execution_time_ms=duration_ms,
                )

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                return ExecutionResult(
                    status=ExecutionStatus.RUNTIME_ERROR,
                    stdout="",
                    stderr=f"Sandbox process execution failed: {str(e)}",
                    exit_code=1,
                    execution_time_ms=duration_ms,
                )

        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass


# Default sandbox instance
development_sandbox = DevelopmentSubprocessSandbox()
