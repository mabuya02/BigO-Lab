from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.common import APIModel, TimestampedModel


class ComplexityFitRead(APIModel):
    label: str
    big_o: str
    quality: float
    rmse: float
    normalized_rmse: float
    slope: float
    intercept: float
    valid: bool
    notes: str


class ComplexityEstimateRead(TimestampedModel):
    id: str
    experiment_id: str | None
    metric_name: str
    estimated_class: str
    confidence: float
    sample_count: int
    explanation: str
    alternatives: list[ComplexityFitRead] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)
