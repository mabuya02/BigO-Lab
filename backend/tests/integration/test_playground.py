from __future__ import annotations

import os
import unittest
from contextlib import contextmanager

from fastapi.testclient import TestClient

os.environ["REDIS_REQUIRED"] = "false"
os.environ["AUTO_CREATE_TABLES"] = "false"
os.environ["EXECUTION_BACKEND"] = "local"
os.environ["EXECUTION_QUEUE_BACKEND"] = "local"
os.environ["EXECUTION_ALLOW_LOCAL_FALLBACK"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-with-sufficient-length"

from app.core.settings import get_settings  # noqa: E402

get_settings.cache_clear()

from app.main import create_app  # noqa: E402


@contextmanager
def get_client():
    with TestClient(create_app()) as client:
        yield client


class PlaygroundApiTests(unittest.TestCase):
    def test_status_reports_stateless_mode(self) -> None:
        with get_client() as client:
            response = client.get("/api/v1/playground/status")
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["mode"], "stateless-playground")
            self.assertIn("sandboxed execution service", payload["description"])
            self.assertIn("backend_status", payload)
            self.assertEqual(payload["backend_status"]["execution_backend"], "local")

    def test_run_executes_code_without_auth(self) -> None:
        with get_client() as client:
            response = client.post(
                "/api/v1/playground/run",
                json={
                    "code": "print('hello playground')\n",
                    "input": "",
                    "backend": "local",
                    "instrument": False,
                },
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["input"], "")
            self.assertEqual(payload["backend_requested"], "local")
            self.assertEqual(payload["execution"]["status"], "completed")
            self.assertEqual(payload["execution"]["stdout"], "hello playground\n")

    def test_experiment_runs_multiple_sizes_and_returns_metrics(self) -> None:
        with get_client() as client:
            response = client.post(
                "/api/v1/playground/experiment",
                json={
                    "code": (
                        "import json\n"
                        "values = json.loads(input())\n"
                        "total = 0\n"
                        "for left in values:\n"
                        "    for right in values:\n"
                        "        total += left + right\n"
                        "print(total)\n"
                    ),
                    "input_sizes": [2, 4],
                    "input_kind": "array",
                    "input_profile": "sorted",
                    "repetitions": 2,
                    "backend": "local",
                    "instrument": True,
                },
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["backend_requested"], "local")
            self.assertEqual(payload["repetitions"], 2)
            self.assertEqual(len(payload["runs"]), 4)
            self.assertEqual(payload["metrics_snapshot"]["summary"]["total_runs"], 4)
            self.assertGreater(payload["metrics_snapshot"]["summary"]["total_line_executions"], 0)
            first_run = payload["runs"][0]
            self.assertEqual(first_run["execution"]["status"], "completed")
            self.assertIsNotNone(first_run["execution"]["instrumentation"])
