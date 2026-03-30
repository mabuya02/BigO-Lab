from __future__ import annotations

from app.schemas.common import TimestampedModel


class UserRead(TimestampedModel):
    id: str
    email: str
    full_name: str | None
    is_active: bool
