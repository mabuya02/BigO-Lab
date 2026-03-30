from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from app.schemas.common import APIModel

ExecutionBackend = Literal["auto", "docker", "local"]
ExecutionResultStatus = Literal["completed", "failed", "timeout"]
ExecutionJobStatus = Literal["queued", "running", "completed", "failed", "timeout"]


class CodeExecutionRequest(APIModel):
    code: str = Field(min_length=1)
    stdin: str = ""
    language: str = Field(default="python")
    timeout_seconds: int | None = Field(default=None, ge=1, le=30)
    memory_limit_mb: int | None = Field(default=None, ge=32, le=1024)
    backend: ExecutionBackend = "auto"
    instrument: bool = False

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized != "python":
            raise ValueError("Phase 2 execution currently supports Python only")
        return normalized


class CodeExecutionResult(APIModel):
    status: ExecutionResultStatus
    stdout: str
    stderr: str
    exit_code: int | None
    runtime_ms: int
    backend: str
    timed_out: bool = False
    truncated_stdout: bool = False
    truncated_stderr: bool = False
    instrumentation: "ExecutionInstrumentationReport | None" = None


class ExecutionInstrumentationReport(APIModel):
    line_counts: dict[int, int]
    function_call_counts: dict[str, int]
    loop_iteration_counts: dict[str, int]
    line_numbers: list[int]
    function_names: list[str]
    loop_line_numbers: list[int]


class CodeExecutionJob(APIModel):
    job_id: str
    status: ExecutionJobStatus
    queue_backend: str
    backend_requested: ExecutionBackend
    backend_used: str | None = None
    submitted_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    result: CodeExecutionResult | None = None
    error: str | None = None


class ExecutionBackendStatus(APIModel):
    execution_backend: str
    queue_backend: str
    local_fallback_enabled: bool
    docker_cli_available: bool
    docker_image_available: bool
    dramatiq_available: bool
    redis_configured: bool
    sandbox_image: str
    default_timeout_seconds: int
    max_timeout_seconds: int
    memory_limit_mb: int
