from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

from app.schemas.common import APIModel


class ShareCreateRequest(APIModel):
    kind: str = Field(default="playground-session", min_length=1, max_length=80)
    label: str | None = Field(default=None, max_length=160)
    data: dict[str, Any] = Field(default_factory=dict)
    expires_in_seconds: int = Field(default=24 * 60 * 60, ge=1, le=30 * 24 * 60 * 60)


class ShareResolveRequest(APIModel):
    token: str = Field(min_length=1)


class SharePayloadRead(APIModel):
    token: str
    share_path: str
    kind: str
    label: str | None
    data: dict[str, Any]
    created_at: datetime
    expires_at: datetime | None
    payload_size_bytes: int
    signature_version: str


class ShareResolveResponse(SharePayloadRead):
    resolved_at: datetime

    @field_validator("resolved_at")
    @classmethod
    def ensure_datetime(cls, value: datetime) -> datetime:
        return value
