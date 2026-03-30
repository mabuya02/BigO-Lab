from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import api_router
from app.core.logger import configure_logging
from app.core.performance import timer
from app.core.runtime import get_rate_limiter
from app.core.settings import get_settings

configure_logging()


def _client_identifier(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "anonymous"


def _rate_limit_scope(path: str) -> str | None:
    if path.startswith("/api/v1/health") or path.startswith("/api/v1/presets") or path.startswith("/api/v1/playground/status"):
        return "read"
    if path in {"/api/v1/playground/experiment", "/api/v1/execution/jobs"}:
        return "heavy"
    if path in {
        "/api/v1/playground/run",
        "/api/v1/execution/run",
        "/api/v1/comparisons/compare",
        "/api/v1/explanations/generate",
        "/api/v1/shares",
        "/api/v1/shares/resolve",
    }:
        return "compute"
    if path.startswith("/api/v1/execution/jobs/"):
        return "read"
    return None


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def apply_runtime_controls(request: Request, call_next):
        request_id = uuid4().hex
        request.state.request_id = request_id
        rate_limit_headers: dict[str, str] = {}
        settings = get_settings()

        if request.url.path.startswith(settings.api_prefix):
            if request.method in {"POST", "PUT", "PATCH"}:
                body = await request.body()
                if len(body) > settings.request_max_body_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": "Request body exceeds the configured size limit."},
                        headers={"X-Request-Id": request_id},
                    )

            scope = _rate_limit_scope(request.url.path)
            if settings.rate_limit_enabled and scope is not None:
                decision = get_rate_limiter(scope).allow(_client_identifier(request))
                rate_limit_headers = {
                    "X-RateLimit-Limit": str(decision.limit),
                    "X-RateLimit-Remaining": str(decision.remaining),
                    "X-RateLimit-Reset": str(int(decision.reset_at)),
                }
                if not decision.allowed:
                    rate_limit_headers["Retry-After"] = str(decision.retry_after_seconds)
                    rate_limit_headers["X-Request-Id"] = request_id
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Rate limit exceeded. Please retry later."},
                        headers=rate_limit_headers,
                    )

        with timer() as timing:
            response = await call_next(request)

        response.headers["X-Request-Id"] = request_id
        if settings.request_timing_headers_enabled:
            response.headers["X-Request-Duration-Ms"] = f"{timing['elapsed_ms']:.2f}"
        for header, value in rate_limit_headers.items():
            response.headers[header] = value
        return response

    @app.get("/", tags=["meta"])
    def root() -> dict[str, str]:
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs_url": "/docs",
        }

    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
