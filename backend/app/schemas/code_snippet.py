from __future__ import annotations

from pydantic import Field

from app.schemas.common import APIModel, TimestampedModel
from app.utils.constants import DEFAULT_LANGUAGE


class CodeSnippetCreate(APIModel):
    title: str = Field(min_length=1, max_length=160)
    language: str = Field(default=DEFAULT_LANGUAGE, min_length=2, max_length=50)
    code: str = Field(min_length=1)


class CodeSnippetUpdate(APIModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    language: str | None = Field(default=None, min_length=2, max_length=50)
    code: str | None = Field(default=None, min_length=1)


class CodeSnippetRead(TimestampedModel):
    id: str
    project_id: str
    author_id: str
    title: str
    language: str
    code: str
    version: int
    is_active: bool
