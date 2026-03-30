from __future__ import annotations

from pydantic import Field

from app.schemas.common import APIModel, TimestampedModel


class ProjectCreate(APIModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None


class ProjectRead(TimestampedModel):
    id: str
    owner_id: str
    name: str
    description: str | None
