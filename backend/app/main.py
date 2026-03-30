from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.logger import configure_logging
from app.core.settings import get_settings
from app.db.session import init_db

configure_logging()


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if settings.auto_create_tables:
            init_db()
        yield

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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
