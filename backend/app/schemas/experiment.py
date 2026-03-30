from __future__ import annotations

from pydantic import Field, field_validator

from app.schemas.common import APIModel, TimestampedModel
from app.schemas.complexity import ComplexityEstimateRead
from app.schemas.experiment_run import ExperimentRunRead
from app.schemas.metrics import ExperimentMetricsSnapshot
from app.utils.constants import DEFAULT_EXPERIMENT_STATUS, DEFAULT_LANGUAGE


class ExperimentCreate(APIModel):
    name: str = Field(min_length=1, max_length=160)
    snippet_id: str | None = None
    language: str = Field(default=DEFAULT_LANGUAGE, min_length=2, max_length=50)
    input_kind: str = Field(default="array", min_length=2, max_length=50)
    input_profile: str | None = Field(default=None, max_length=80)
    input_sizes: list[int] = Field(default_factory=list)
    repetitions: int = Field(default=1, ge=1, le=100)

    @field_validator("input_sizes")
    @classmethod
    def validate_input_sizes(cls, sizes: list[int]) -> list[int]:
        if any(size <= 0 for size in sizes):
            raise ValueError("All input sizes must be positive integers")
        return sizes


class ExperimentRead(TimestampedModel):
    id: str
    project_id: str
    snippet_id: str | None
    created_by_id: str
    name: str
    language: str
    status: str = DEFAULT_EXPERIMENT_STATUS
    input_kind: str
    input_profile: str | None
    input_sizes: list[int]
    repetitions: int


class ExperimentExecuteRequest(APIModel):
    backend: str = "auto"
    refresh_complexity: bool = True


class ExperimentDetail(ExperimentRead):
    runs: list[ExperimentRunRead] = Field(default_factory=list)
    metrics_snapshot: ExperimentMetricsSnapshot | None = None
    latest_complexity_estimate: ComplexityEstimateRead | None = None
