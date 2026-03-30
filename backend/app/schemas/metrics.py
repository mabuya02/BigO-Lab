from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from app.schemas.common import APIModel, TimestampedModel

MetricScope = Literal["line", "function"]


class LineMetricCreate(APIModel):
    line_number: int = Field(gt=0)
    execution_count: int = Field(default=0, ge=0)
    total_time_ms: float = Field(default=0.0, ge=0.0)
    percentage_of_total: float = Field(default=0.0, ge=0.0)
    nesting_depth: int = Field(default=0, ge=0)
    loop_iterations: int = Field(default=0, ge=0)
    branch_visits: int = Field(default=0, ge=0)


class LineMetricRead(TimestampedModel):
    id: str
    experiment_run_id: str
    line_number: int
    execution_count: int
    total_time_ms: float
    percentage_of_total: float
    nesting_depth: int
    loop_iterations: int
    branch_visits: int


class FunctionMetricCreate(APIModel):
    function_name: str = Field(min_length=1, max_length=160)
    qualified_name: str | None = Field(default=None, max_length=255)
    call_count: int = Field(default=0, ge=0)
    total_time_ms: float = Field(default=0.0, ge=0.0)
    self_time_ms: float = Field(default=0.0, ge=0.0)
    max_depth: int = Field(default=0, ge=0)
    is_recursive: bool = False


class FunctionMetricRead(TimestampedModel):
    id: str
    experiment_run_id: str
    function_name: str
    qualified_name: str | None
    call_count: int
    total_time_ms: float
    self_time_ms: float
    max_depth: int
    is_recursive: bool


class MetricPoint(APIModel):
    input_size: int = Field(gt=0)
    value: float = Field(ge=0.0)


class MetricSeries(APIModel):
    label: str
    points: list[MetricPoint] = Field(default_factory=list)

    @field_validator("points")
    @classmethod
    def validate_points(cls, points: list[MetricPoint]) -> list[MetricPoint]:
        points.sort(key=lambda point: point.input_size)
        return points


class MetricSummary(APIModel):
    total_runs: int = Field(ge=0)
    input_sizes: list[int] = Field(default_factory=list)
    average_runtime_ms: float = Field(ge=0.0)
    min_runtime_ms: float = Field(ge=0.0)
    max_runtime_ms: float = Field(ge=0.0)
    total_runtime_ms: float = Field(ge=0.0)
    total_line_executions: int = Field(ge=0)
    total_function_calls: int = Field(ge=0)
    dominant_line_number: int | None = None
    dominant_function_name: str | None = None
    runtime_series: MetricSeries = Field(default_factory=lambda: MetricSeries(label="runtime_ms"))
    operations_series: MetricSeries = Field(default_factory=lambda: MetricSeries(label="operations"))


class AggregatedLineMetric(APIModel):
    line_number: int
    total_execution_count: int = Field(ge=0)
    total_time_ms: float = Field(ge=0.0)
    average_time_ms: float = Field(ge=0.0)
    percentage_of_total: float = Field(ge=0.0)
    nesting_depth: int = Field(ge=0)
    loop_iterations: int = Field(ge=0)
    branch_visits: int = Field(ge=0)


class AggregatedFunctionMetric(APIModel):
    function_name: str
    qualified_name: str | None = None
    total_call_count: int = Field(ge=0)
    total_time_ms: float = Field(ge=0.0)
    average_time_ms: float = Field(ge=0.0)
    self_time_ms: float = Field(ge=0.0)
    max_depth: int = Field(ge=0)
    is_recursive: bool = False


class ExperimentMetricsSnapshot(APIModel):
    summary: MetricSummary
    line_metrics: list[AggregatedLineMetric] = Field(default_factory=list)
    function_metrics: list[AggregatedFunctionMetric] = Field(default_factory=list)
