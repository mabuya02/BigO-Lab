from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from app.schemas.common import APIModel
from app.schemas.metrics import ExperimentMetricsSnapshot

ComparisonWinner = Literal["left", "right", "tie"]
ComparisonHotspotKind = Literal["line", "function"]


class ComparisonComplexityInput(APIModel):
    estimated_class: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    sample_count: int = Field(default=0, ge=0)
    explanation: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)


class ComparisonHotspotSummary(APIModel):
    kind: ComparisonHotspotKind
    identifier: str
    value: float = Field(ge=0.0)
    share_of_total: float = Field(ge=0.0, le=1.0)


class ComparisonSubjectInput(APIModel):
    label: str = Field(min_length=1, max_length=160)
    metrics: ExperimentMetricsSnapshot
    complexity_estimate: ComparisonComplexityInput | None = None


class ComparisonSubjectSummary(APIModel):
    label: str
    total_runs: int = Field(ge=0)
    average_runtime_ms: float = Field(ge=0.0)
    total_runtime_ms: float = Field(ge=0.0)
    total_line_executions: int = Field(ge=0)
    total_function_calls: int = Field(ge=0)
    runtime_growth_rate: float
    operation_growth_rate: float
    dominant_line_number: int | None = None
    dominant_function_name: str | None = None
    complexity_estimate: ComparisonComplexityInput | None = None
    top_lines: list[ComparisonHotspotSummary] = Field(default_factory=list)
    top_functions: list[ComparisonHotspotSummary] = Field(default_factory=list)


class ComparisonTrendDelta(APIModel):
    metric_name: str
    left_start: float = Field(ge=0.0)
    left_end: float = Field(ge=0.0)
    right_start: float = Field(ge=0.0)
    right_end: float = Field(ge=0.0)
    left_growth_rate: float
    right_growth_rate: float
    delta: float
    percent_change: float
    winner: ComparisonWinner
    interpretation: str


class ComparisonComplexityDelta(APIModel):
    left_class: str | None = None
    right_class: str | None = None
    left_rank: int | None = None
    right_rank: int | None = None
    delta: int | None = None
    confidence_delta: float | None = None
    winner: ComparisonWinner
    interpretation: str


class ComparisonHotspotComparison(APIModel):
    kind: ComparisonHotspotKind
    left_identifier: str | None = None
    right_identifier: str | None = None
    left_value: float = Field(ge=0.0)
    right_value: float = Field(ge=0.0)
    left_share_of_total: float = Field(ge=0.0, le=1.0)
    right_share_of_total: float = Field(ge=0.0, le=1.0)
    delta: float
    winner: ComparisonWinner
    interpretation: str


class ComparisonSummary(APIModel):
    overall_winner: ComparisonWinner
    confidence: float = Field(ge=0.0, le=1.0)
    verdict: str
    tradeoffs: list[str] = Field(default_factory=list)


class ComparisonRequest(APIModel):
    left: ComparisonSubjectInput
    right: ComparisonSubjectInput

    @model_validator(mode="after")
    def validate_distinct_labels(self) -> "ComparisonRequest":
        if self.left.label.strip().lower() == self.right.label.strip().lower():
            raise ValueError("Comparison labels must be distinct")
        return self


class ComparisonReport(APIModel):
    left: ComparisonSubjectSummary
    right: ComparisonSubjectSummary
    runtime: ComparisonTrendDelta
    operations: ComparisonTrendDelta
    complexity: ComparisonComplexityDelta
    hotspots: list[ComparisonHotspotComparison] = Field(default_factory=list)
    summary: ComparisonSummary
