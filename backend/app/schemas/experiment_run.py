from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from app.schemas.common import APIModel, TimestampedModel
from app.schemas.metrics import FunctionMetricRead, LineMetricRead, MetricSummary

ExperimentRunStatus = Literal["queued", "running", "completed", "failed", "timeout"]


class ExperimentRunCreate(APIModel):
    experiment_id: str
    input_size: int = Field(gt=0)
    repetition_index: int = Field(default=0, ge=0)
    input_profile: str | None = Field(default=None, max_length=80)
    input_payload: dict | list | str | int | float | bool | None = None
    status: ExperimentRunStatus = "queued"
    backend: str | None = Field(default=None, max_length=50)

    @field_validator("experiment_id")
    @classmethod
    def validate_experiment_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("experiment_id cannot be empty")
        return value


class ExperimentRunUpdate(APIModel):
    status: ExperimentRunStatus | None = None
    backend: str | None = Field(default=None, max_length=50)
    runtime_ms: int | None = Field(default=None, ge=0)
    stdout: str | None = None
    stderr: str | None = None
    exit_code: int | None = None
    timed_out: bool | None = None
    truncated_stdout: bool | None = None
    truncated_stderr: bool | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class ExperimentRunRead(TimestampedModel):
    id: str
    experiment_id: str
    input_size: int
    repetition_index: int
    input_profile: str | None
    input_payload: dict | list | str | int | float | bool | None
    status: ExperimentRunStatus
    backend: str | None
    runtime_ms: int | None
    stdout: str | None
    stderr: str | None
    exit_code: int | None
    timed_out: bool
    truncated_stdout: bool
    truncated_stderr: bool
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    line_metrics: list[LineMetricRead] = Field(default_factory=list)
    function_metrics: list[FunctionMetricRead] = Field(default_factory=list)
    summary: MetricSummary | None = None
