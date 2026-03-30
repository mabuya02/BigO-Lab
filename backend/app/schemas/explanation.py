from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, field_validator

from app.schemas.common import APIModel
from app.schemas.complexity import ComplexityEstimateRead
from app.schemas.metrics import ExperimentMetricsSnapshot


class ExplanationRequest(APIModel):
    metrics_snapshot: ExperimentMetricsSnapshot
    complexity_estimate: ComplexityEstimateRead | None = None
    max_sections: int = Field(default=5, ge=1, le=10)


class ExplanationSection(APIModel):
    title: str
    body: str
    evidence: list[str] = Field(default_factory=list)
    kind: Literal["summary", "dominance", "loop", "complexity", "caveat"] = "summary"

    @field_validator("evidence")
    @classmethod
    def normalize_evidence(cls, evidence: list[str]) -> list[str]:
        return [item for item in evidence if item.strip()]


class ExplanationResponse(APIModel):
    headline: str
    summary: str
    complexity_class: str | None = None
    confidence: float | None = None
    dominant_line_number: int | None = None
    dominant_function_name: str | None = None
    sections: list[ExplanationSection] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)


__all__ = [
    "ExplanationRequest",
    "ExplanationResponse",
    "ExplanationSection",
]
