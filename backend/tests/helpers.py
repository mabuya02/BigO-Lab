from __future__ import annotations

import os
from contextlib import contextmanager

from fastapi.testclient import TestClient

os.environ["REDIS_REQUIRED"] = "false"
os.environ["AUTO_CREATE_TABLES"] = "false"
os.environ["SECRET_KEY"] = "test-secret-key-with-sufficient-length"
os.environ["EXECUTION_BACKEND"] = "local"
os.environ["EXECUTION_QUEUE_BACKEND"] = "local"
os.environ["EXECUTION_ALLOW_LOCAL_FALLBACK"] = "true"

from app.core.settings import get_settings  # noqa: E402

get_settings.cache_clear()

from app.main import create_app  # noqa: E402


def reset_database() -> None:
    return None


@contextmanager
def get_client():
    with TestClient(create_app()) as client:
        yield client
