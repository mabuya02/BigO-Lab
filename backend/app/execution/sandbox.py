from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SandboxLimits:
    timeout_seconds: int
    memory_limit_mb: int
    cpu_limit: float
    output_limit_bytes: int


@dataclass(slots=True)
class SandboxExecutionResult:
    status: str
    stdout: str
    stderr: str
    exit_code: int | None
    runtime_ms: int
    backend: str
    timed_out: bool = False
    truncated_stdout: bool = False
    truncated_stderr: bool = False
