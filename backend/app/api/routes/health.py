from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.settings import get_settings
from app.db.session import check_database
from app.services.health_service import check_redis

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def live() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "backend",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ready")
def ready() -> JSONResponse:
    settings = get_settings()

    checks = {
        "database": {
            "ok": check_database(),
            "required": True,
        },
        "redis": {
            "ok": check_redis(settings.redis_url),
            "required": settings.redis_required,
        },
    }

    ready_to_serve = all(check["ok"] or not check["required"] for check in checks.values())
    perfect = all(check["ok"] for check in checks.values())

    payload = {
        "status": "ok" if perfect else "degraded" if ready_to_serve else "error",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }

    return JSONResponse(status_code=200 if ready_to_serve else 503, content=payload)
