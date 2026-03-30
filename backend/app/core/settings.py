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

    # PostgreSQL
    db_driver: str = "postgresql+psycopg2"
    db_host: str = "127.0.0.1"
    db_port: int = 5432
    db_name: str = "bigOlab"
    db_user: str = "mabuya"
    db_password: str = "millenium"

    @property
    def database_url(self) -> str:
        return f"{self.db_driver}://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_required: bool = False

    # Signing key for shares
    secret_key: str = Field(default="change-this-in-production", min_length=16)

    # Execution
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

    # Rate limiting & caching
    request_max_body_bytes: int = 262144
    request_timing_headers_enabled: bool = True
    rate_limit_enabled: bool = True
    rate_limit_backend: str = "memory"
    rate_limit_window_seconds: int = 60
    rate_limit_compute_limit: int = 20
    rate_limit_heavy_limit: int = 8
    rate_limit_read_limit: int = 120
    cache_enabled: bool = True
    cache_backend: str = "memory"
    cache_default_ttl_seconds: int = 120
    cache_presets_ttl_seconds: int = 600
    cache_analysis_ttl_seconds: int = 180
    cache_share_ttl_seconds: int = 300

    # Explanation provider
    explanation_provider: str = "heuristic"
    explanation_allow_fallback: bool = True
    ollama_api_base_url: str = "https://ollama.com/api"
    ollama_api_key: str | None = None
    ollama_model: str = "gpt-oss:120b"
    ollama_timeout_seconds: float = 20.0
    ollama_temperature: float = 0.2

    # CORS
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
        db_driver=os.getenv("DB_DRIVER", "postgresql+psycopg2"),
        db_host=os.getenv("DB_HOST", "127.0.0.1"),
        db_port=int(os.getenv("DB_PORT", "5432")),
        db_name=os.getenv("DB_NAME", "bigOlab"),
        db_user=os.getenv("DB_USER", "mabuya"),
        db_password=os.getenv("DB_PASSWORD", "millenium"),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        redis_required=_as_bool(os.getenv("REDIS_REQUIRED"), False),
        secret_key=os.getenv("SECRET_KEY", "change-this-in-production"),
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
        request_max_body_bytes=int(os.getenv("REQUEST_MAX_BODY_BYTES", "262144")),
        request_timing_headers_enabled=_as_bool(os.getenv("REQUEST_TIMING_HEADERS_ENABLED"), True),
        rate_limit_enabled=_as_bool(os.getenv("RATE_LIMIT_ENABLED"), True),
        rate_limit_backend=os.getenv("RATE_LIMIT_BACKEND", "memory"),
        rate_limit_window_seconds=int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")),
        rate_limit_compute_limit=int(os.getenv("RATE_LIMIT_COMPUTE_LIMIT", "20")),
        rate_limit_heavy_limit=int(os.getenv("RATE_LIMIT_HEAVY_LIMIT", "8")),
        rate_limit_read_limit=int(os.getenv("RATE_LIMIT_READ_LIMIT", "120")),
        cache_enabled=_as_bool(os.getenv("CACHE_ENABLED"), True),
        cache_backend=os.getenv("CACHE_BACKEND", "memory"),
        cache_default_ttl_seconds=int(os.getenv("CACHE_DEFAULT_TTL_SECONDS", "120")),
        cache_presets_ttl_seconds=int(os.getenv("CACHE_PRESETS_TTL_SECONDS", "600")),
        cache_analysis_ttl_seconds=int(os.getenv("CACHE_ANALYSIS_TTL_SECONDS", "180")),
        cache_share_ttl_seconds=int(os.getenv("CACHE_SHARE_TTL_SECONDS", "300")),
        explanation_provider=os.getenv("EXPLANATION_PROVIDER", "heuristic"),
        explanation_allow_fallback=_as_bool(os.getenv("EXPLANATION_ALLOW_FALLBACK"), True),
        ollama_api_base_url=os.getenv("OLLAMA_API_BASE_URL", "https://ollama.com/api"),
        ollama_api_key=os.getenv("OLLAMA_API_KEY"),
        ollama_model=os.getenv("OLLAMA_MODEL", "gpt-oss:120b"),
        ollama_timeout_seconds=float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "20")),
        ollama_temperature=float(os.getenv("OLLAMA_TEMPERATURE", "0.2")),
        cors_allowed_origins=origins,
    )
