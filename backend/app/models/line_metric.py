from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db import Base
from app.utils.helpers import utcnow


class LineMetric(Base):
    __tablename__ = "line_metrics"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    experiment_run_id = Column(
        String(36),
        ForeignKey("experiment_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    line_number = Column(Integer, nullable=False, index=True)
    execution_count = Column(Integer, nullable=False, default=0)
    total_time_ms = Column(Float, nullable=False, default=0.0)
    percentage_of_total = Column(Float, nullable=False, default=0.0)
    nesting_depth = Column(Integer, nullable=False, default=0)
    loop_iterations = Column(Integer, nullable=False, default=0)
    branch_visits = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    run = relationship("ExperimentRun", back_populates="line_metrics")
