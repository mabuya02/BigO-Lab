from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.db.base.base import Base
from app.utils.helpers import utcnow


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    owner = relationship("User", back_populates="projects")
    snippets = relationship(
        "CodeSnippet",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="desc(CodeSnippet.updated_at)",
    )
    experiments = relationship(
        "Experiment",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="desc(Experiment.updated_at)",
    )
