from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import backref, relationship

from app.db.base.base import Base
from app.utils.helpers import utcnow


class ExperimentRun(Base):
    __tablename__ = "experiment_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    experiment_id = Column(
        String(36),
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    input_size = Column(Integer, nullable=False, index=True)
    repetition_index = Column(Integer, nullable=False, default=0)
    input_profile = Column(String(80), nullable=True)
    input_payload = Column(JSON, nullable=True)
    status = Column(String(50), nullable=False, default="queued")
    backend = Column(String(50), nullable=True)
    runtime_ms = Column(Integer, nullable=True)
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)
    exit_code = Column(Integer, nullable=True)
    timed_out = Column(Boolean, nullable=False, default=False)
    truncated_stdout = Column(Boolean, nullable=False, default=False)
    truncated_stderr = Column(Boolean, nullable=False, default=False)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    experiment = relationship("Experiment", backref=backref("runs", lazy="selectin"))
    line_metrics = relationship(
        "LineMetric",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="LineMetric.line_number",
    )
    function_metrics = relationship(
        "FunctionMetric",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="FunctionMetric.function_name",
    )
