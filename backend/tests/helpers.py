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

from app.db.base.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import create_app  # noqa: E402


def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_client():
    reset_database()
    with TestClient(create_app()) as client:
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
