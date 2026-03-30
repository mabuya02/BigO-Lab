from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.orm import relationship

from app.db.base.base import Base
from app.utils.helpers import utcnow


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), nullable=False, unique=True, index=True)
    full_name = Column(String(255), nullable=True)
    password_hash = Column(String(512), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    projects = relationship(
        "Project",
        back_populates="owner",
        cascade="all, delete-orphan",
        order_by="desc(Project.updated_at)",
    )
    snippets = relationship("CodeSnippet", back_populates="author")
    experiments = relationship("Experiment", back_populates="created_by")
