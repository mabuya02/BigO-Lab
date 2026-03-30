from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone

from fastapi.security import OAuth2PasswordBearer

from app.core.settings import get_settings

PBKDF2_ITERATIONS = 260_000

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class TokenValidationError(ValueError):
    pass


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(f"{data}{padding}".encode("utf-8"))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return (
        "pbkdf2_sha256$"
        f"{PBKDF2_ITERATIONS}$"
        f"{base64.urlsafe_b64encode(salt).decode('utf-8')}$"
        f"{base64.urlsafe_b64encode(digest).decode('utf-8')}"
    )


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        _, iterations, salt_b64, digest_b64 = stored_hash.split("$", 3)
    except ValueError:
        return False

    salt = base64.urlsafe_b64decode(salt_b64.encode("utf-8"))
    expected_digest = base64.urlsafe_b64decode(digest_b64.encode("utf-8"))
    calculated_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        int(iterations),
    )
    return hmac.compare_digest(expected_digest, calculated_digest)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expiry = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    header = {
        "alg": settings.jwt_algorithm,
        "typ": "JWT",
    }
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expiry.timestamp()),
        "type": "access",
    }

    header_segment = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_segment = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    signature = hmac.new(
        settings.secret_key.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    return f"{header_segment}.{payload_segment}.{_b64url_encode(signature)}"


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    try:
        header_segment, payload_segment, signature_segment = token.split(".", 2)
    except ValueError as exc:
        raise TokenValidationError("Token structure is invalid") from exc

    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    expected_signature = hmac.new(
        settings.secret_key.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    provided_signature = _b64url_decode(signature_segment)

    if not hmac.compare_digest(expected_signature, provided_signature):
        raise TokenValidationError("Token signature is invalid")

    try:
        payload = json.loads(_b64url_decode(payload_segment).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise TokenValidationError("Token payload is invalid") from exc

    expiry = payload.get("exp")
    if not isinstance(expiry, int):
        raise TokenValidationError("Token expiry is invalid")
    if expiry < int(datetime.now(timezone.utc).timestamp()):
        raise TokenValidationError("Token has expired")

    return payload
