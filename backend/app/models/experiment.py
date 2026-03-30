from __future__ import annotations

import uuid

from sqlalchemy import JSON, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.db import Base
from app.utils.helpers import utcnow


class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(160), nullable=False)
    language = Column(String(50), nullable=False, default="python")
    status = Column(String(50), nullable=False, default="draft")
    input_kind = Column(String(50), nullable=False, default="array")
    input_profile = Column(String(80), nullable=True)
    input_sizes = Column(JSON, nullable=False, default=list)
    repetitions = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    complexity_estimates = relationship(
        "ComplexityEstimate",
        back_populates="experiment",
        cascade="all, delete-orphan",
        order_by="desc(ComplexityEstimate.created_at)",
    )
