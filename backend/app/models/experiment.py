from __future__ import annotations

import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base.base import Base
from app.utils.constants import DEFAULT_EXPERIMENT_STATUS, DEFAULT_LANGUAGE
from app.utils.helpers import utcnow


class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    snippet_id = Column(String(36), ForeignKey("code_snippets.id", ondelete="SET NULL"), nullable=True, index=True)
    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(160), nullable=False)
    language = Column(String(50), nullable=False, default=DEFAULT_LANGUAGE)
    status = Column(String(50), nullable=False, default=DEFAULT_EXPERIMENT_STATUS)
    input_profile = Column(String(80), nullable=True)
    input_sizes = Column(JSON, nullable=False, default=list)
    repetitions = Column(Integer, nullable=False, default=1)
    input_kind = Column(String(50), nullable=False, default="array")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    created_by = relationship("User", back_populates="experiments")
    project = relationship("Project", back_populates="experiments")
    snippet = relationship("CodeSnippet", back_populates="experiments")
    complexity_estimates = relationship(
        "ComplexityEstimate",
        back_populates="experiment",
        cascade="all, delete-orphan",
        order_by="desc(ComplexityEstimate.created_at)",
    )
