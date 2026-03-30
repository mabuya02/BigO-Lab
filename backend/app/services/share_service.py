from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import timedelta
from typing import Any

from fastapi import HTTPException, status

from app.core.settings import get_settings
from app.schemas.share import ShareCreateRequest, SharePayloadRead, ShareResolveRequest, ShareResolveResponse
from app.utils.helpers import utcnow


class ShareService:
    SIGNATURE_VERSION = "v1"

    @classmethod
    def create_share_payload(cls, payload: ShareCreateRequest) -> SharePayloadRead:
        created_at = utcnow()
        expires_at = created_at + timedelta(seconds=payload.expires_in_seconds) if payload.expires_in_seconds else None
        body = {
            "kind": payload.kind,
            "label": payload.label,
            "data": payload.data,
            "created_at": created_at.isoformat(),
            "expires_at": expires_at.isoformat() if expires_at is not None else None,
        }
        token = cls._encode(body)
        return SharePayloadRead(
            token=token,
            share_path=f"/share/{token}",
            kind=payload.kind,
            label=payload.label,
            data=payload.data,
            created_at=created_at,
            expires_at=expires_at,
            payload_size_bytes=len(cls._json_bytes(body)),
            signature_version=cls.SIGNATURE_VERSION,
        )

    @classmethod
    def resolve_share_payload(cls, payload: ShareResolveRequest) -> ShareResolveResponse:
        body = cls._decode(payload.token)
        created_at = cls._parse_datetime(body["created_at"])
        expires_at = cls._parse_datetime(body["expires_at"]) if body.get("expires_at") else None
        if expires_at is not None and utcnow() > expires_at:
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Shared payload has expired")
        return ShareResolveResponse(
            token=payload.token,
            share_path=f"/share/{payload.token}",
            kind=str(body["kind"]),
            label=body.get("label"),
            data=dict(body.get("data", {})),
            created_at=created_at,
            expires_at=expires_at,
            payload_size_bytes=len(cls._json_bytes(body)),
            signature_version=str(body.get("signature_version", cls.SIGNATURE_VERSION)),
            resolved_at=utcnow(),
        )

    @classmethod
    def _encode(cls, body: dict[str, Any]) -> str:
        payload = {
            "v": cls.SIGNATURE_VERSION,
            "body": body,
        }
        payload_bytes = cls._json_bytes(payload)
        payload_part = cls._b64encode(payload_bytes)
        signature = cls._sign(payload_part)
        return f"{cls.SIGNATURE_VERSION}.{payload_part}.{signature}"

    @classmethod
    def _decode(cls, token: str) -> dict[str, Any]:
        parts = token.split(".")
        if len(parts) != 3 or parts[0] != cls.SIGNATURE_VERSION:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid share token")
        _, payload_part, signature = parts
        expected_signature = cls._sign(payload_part)
        if not hmac.compare_digest(signature, expected_signature):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid share token signature")
        try:
            payload = json.loads(cls._b64decode(payload_part))
        except (ValueError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid share token payload") from exc
        body = payload.get("body")
        if not isinstance(body, dict):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid share token payload")
        return body

    @classmethod
    def _sign(cls, payload_part: str) -> str:
        secret = get_settings().secret_key.encode("utf-8")
        digest = hmac.new(secret, payload_part.encode("utf-8"), hashlib.sha256).digest()
        return cls._b64encode(digest)

    @staticmethod
    def _json_bytes(payload: Any) -> bytes:
        return json.dumps(payload, separators=(",", ":"), sort_keys=True, default=ShareService._json_default).encode("utf-8")

    @staticmethod
    def _json_default(value: Any) -> Any:
        if hasattr(value, "isoformat"):
            return value.isoformat()
        if isinstance(value, set):
            return sorted(value)
        return str(value)

    @staticmethod
    def _b64encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")

    @staticmethod
    def _b64decode(data: str) -> str:
        padding = "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode(f"{data}{padding}").decode("utf-8")

    @staticmethod
    def _parse_datetime(value: str) -> Any:
        from datetime import datetime

        return datetime.fromisoformat(value)
