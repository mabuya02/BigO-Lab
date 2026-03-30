from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base.base import Base
from app.utils.constants import DEFAULT_LANGUAGE
from app.utils.helpers import utcnow


class CodeSnippet(Base):
    __tablename__ = "code_snippets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(160), nullable=False)
    language = Column(String(50), nullable=False, default=DEFAULT_LANGUAGE)
    code = Column(Text, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    author = relationship("User", back_populates="snippets")
    project = relationship("Project", back_populates="snippets")
    experiments = relationship("Experiment", back_populates="snippet")
