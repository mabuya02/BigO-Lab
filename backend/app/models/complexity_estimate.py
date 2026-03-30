from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.db.base.base import Base
from app.utils.helpers import utcnow


class ComplexityEstimate(Base):
    __tablename__ = "complexity_estimates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    experiment_id = Column(
        String(36),
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    metric_name = Column(String(80), nullable=False, default="runtime_ms")
    estimated_class = Column(String(80), nullable=False)
    confidence = Column(Float, nullable=False)
    sample_count = Column(Integer, nullable=False, default=0)
    explanation = Column(Text, nullable=False)
    alternatives = Column(JSON, nullable=False, default=list)
    evidence = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    experiment = relationship("Experiment", back_populates="complexity_estimates")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "metric_name": self.metric_name,
            "estimated_class": self.estimated_class,
            "confidence": self.confidence,
            "sample_count": self.sample_count,
            "explanation": self.explanation,
            "alternatives": self.alternatives,
            "evidence": self.evidence,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
