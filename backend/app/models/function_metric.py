from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base.base import Base
from app.utils.helpers import utcnow


class FunctionMetric(Base):
    __tablename__ = "function_metrics"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    experiment_run_id = Column(
        String(36),
        ForeignKey("experiment_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    function_name = Column(String(160), nullable=False, index=True)
    qualified_name = Column(String(255), nullable=True)
    call_count = Column(Integer, nullable=False, default=0)
    total_time_ms = Column(Float, nullable=False, default=0.0)
    self_time_ms = Column(Float, nullable=False, default=0.0)
    max_depth = Column(Integer, nullable=False, default=0)
    is_recursive = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    run = relationship("ExperimentRun", back_populates="function_metrics")
