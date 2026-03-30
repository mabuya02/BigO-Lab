from __future__ import annotations

import os
import unittest
from contextlib import contextmanager

from fastapi.testclient import TestClient

from app.core.runtime import reset_runtime_state
from app.core.settings import get_settings
from app.main import create_app
from app.services.playground_service import PlaygroundService


@contextmanager
def runtime_client(**env: str):
    original = {key: os.environ.get(key) for key in env}
    try:
        for key, value in env.items():
            os.environ[key] = value
        get_settings.cache_clear()
        reset_runtime_state()
        with TestClient(create_app()) as client:
            yield client
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        get_settings.cache_clear()
        reset_runtime_state()


class RuntimeHardeningTests(unittest.TestCase):
    def test_direct_playground_import_is_stable(self) -> None:
        self.assertTrue(hasattr(PlaygroundService, "run_experiment"))

    def test_request_size_limit_rejects_large_payload(self) -> None:
        with runtime_client(REQUEST_MAX_BODY_BYTES="64") as client:
            response = client.post(
                "/api/v1/playground/run",
                json={
                    "code": "print('x' * 400)\n",
                    "input": "z" * 512,
                    "backend": "local",
                },
            )
            self.assertEqual(response.status_code, 413)
            self.assertIn("X-Request-Id", response.headers)

    def test_rate_limit_applies_to_compute_routes(self) -> None:
        with runtime_client(RATE_LIMIT_COMPUTE_LIMIT="2", RATE_LIMIT_WINDOW_SECONDS="60") as client:
            payload = {
                "code": "print('rate-limited')\n",
                "input": "",
                "backend": "local",
            }
            first = client.post("/api/v1/playground/run", json=payload)
            second = client.post("/api/v1/playground/run", json=payload)
            third = client.post("/api/v1/playground/run", json=payload)

            self.assertEqual(first.status_code, 200)
            self.assertEqual(second.status_code, 200)
            self.assertEqual(third.status_code, 429)
            self.assertIn("Retry-After", third.headers)
            self.assertEqual(third.headers["X-RateLimit-Remaining"], "0")

    def test_request_timing_headers_are_emitted(self) -> None:
        with runtime_client() as client:
            response = client.get("/api/v1/health/live")
            self.assertEqual(response.status_code, 200)
            self.assertIn("X-Request-Id", response.headers)
            self.assertIn("X-Request-Duration-Ms", response.headers)
