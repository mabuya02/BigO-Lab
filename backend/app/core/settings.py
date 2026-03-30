from __future__ import annotations

import os
from functools import lru_cache

from pydantic import BaseModel, Field


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings(BaseModel):
    app_name: str = "Big O Playground API"
    app_env: str = "development"
    app_version: str = "0.1.0"
    debug: bool = True
    api_prefix: str = "/api/v1"

    database_url: str = "sqlite:///./bigo_lab.db"
    redis_url: str = "redis://localhost:6379/0"
    redis_required: bool = False
    auto_create_tables: bool = False

    secret_key: str = Field(default="change-this-in-production", min_length=16)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    execution_backend: str = "auto"
    execution_queue_backend: str = "auto"
    execution_allow_local_fallback: bool = True
    execution_docker_image: str = "big-o-playground-python-sandbox:latest"
    execution_workspace_root: str = "/tmp/big-o-playground-runs"
    execution_default_timeout_seconds: int = 3
    execution_max_timeout_seconds: int = 5
    execution_memory_limit_mb: int = 128
    execution_output_limit_bytes: int = 32768
    execution_cpu_limit: float = 1.0

    cors_allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    raw_origins = os.getenv("CORS_ALLOWED_ORIGINS")
    origins = (
        [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
        if raw_origins
        else ["http://localhost:3000"]
    )

    return Settings(
        app_name=os.getenv("APP_NAME", "Big O Playground API"),
        app_env=os.getenv("APP_ENV", "development"),
        app_version=os.getenv("APP_VERSION", "0.1.0"),
        debug=_as_bool(os.getenv("DEBUG"), True),
        api_prefix=os.getenv("API_PREFIX", "/api/v1"),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./bigo_lab.db"),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        redis_required=_as_bool(os.getenv("REDIS_REQUIRED"), False),
        auto_create_tables=_as_bool(os.getenv("AUTO_CREATE_TABLES"), False),
        secret_key=os.getenv("SECRET_KEY", "change-this-in-production"),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")),
        execution_backend=os.getenv("EXECUTION_BACKEND", "auto"),
        execution_queue_backend=os.getenv("EXECUTION_QUEUE_BACKEND", "auto"),
        execution_allow_local_fallback=_as_bool(os.getenv("EXECUTION_ALLOW_LOCAL_FALLBACK"), True),
        execution_docker_image=os.getenv(
            "EXECUTION_DOCKER_IMAGE",
            "big-o-playground-python-sandbox:latest",
        ),
        execution_workspace_root=os.getenv(
            "EXECUTION_WORKSPACE_ROOT",
            "/tmp/big-o-playground-runs",
        ),
        execution_default_timeout_seconds=int(os.getenv("EXECUTION_DEFAULT_TIMEOUT_SECONDS", "3")),
        execution_max_timeout_seconds=int(os.getenv("EXECUTION_MAX_TIMEOUT_SECONDS", "5")),
        execution_memory_limit_mb=int(os.getenv("EXECUTION_MEMORY_LIMIT_MB", "128")),
        execution_output_limit_bytes=int(os.getenv("EXECUTION_OUTPUT_LIMIT_BYTES", "32768")),
        execution_cpu_limit=float(os.getenv("EXECUTION_CPU_LIMIT", "1.0")),
        cors_allowed_origins=origins,
    )
