from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path

from fastapi.testclient import TestClient

DB_PATH = Path("/tmp/big_o_backend_tests.db")

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["REDIS_REQUIRED"] = "false"
os.environ["AUTO_CREATE_TABLES"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-with-sufficient-length"
os.environ["EXECUTION_BACKEND"] = "local"
os.environ["EXECUTION_QUEUE_BACKEND"] = "local"
os.environ["EXECUTION_ALLOW_LOCAL_FALLBACK"] = "true"

from app.core.settings import get_settings  # noqa: E402

get_settings.cache_clear()

from app.api.routes import auth as auth_routes  # noqa: E402
from app.api.routes import execution as execution_routes  # noqa: E402
from app.api.routes import experiments as experiments_routes  # noqa: E402
from app.api.routes import projects as projects_routes  # noqa: E402
from app.api.routes import snippets as snippets_routes  # noqa: E402
from app.db.base.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import create_app  # noqa: E402


def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_client():
    reset_database()
    app = create_app()
    settings = get_settings()
    app.include_router(auth_routes.router, prefix=settings.api_prefix)
    app.include_router(projects_routes.router, prefix=settings.api_prefix)
    app.include_router(snippets_routes.router, prefix=settings.api_prefix)
    app.include_router(experiments_routes.router, prefix=settings.api_prefix)
    app.include_router(execution_routes.router, prefix=settings.api_prefix)
    with TestClient(app) as client:
        yield client
    engine.dispose()


def auth_headers(client: TestClient) -> dict[str, str]:
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "student@example.com",
            "password": "supersecure123",
            "full_name": "Test Student",
        },
    )
    assert register_response.status_code == 201, register_response.text

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "student@example.com",
            "password": "supersecure123",
        },
    )
    assert login_response.status_code == 200, login_response.text
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
