from __future__ import annotations

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.presets import router as presets_router


def build_client() -> TestClient:
    app = FastAPI()
    app.include_router(presets_router, prefix="/api/v1")
    return TestClient(app)


class PresetApiTests(unittest.TestCase):
    def test_list_presets(self) -> None:
        with build_client() as client:
            response = client.get("/api/v1/presets")
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertIn("presets", payload)
            self.assertTrue(any(item["slug"] == "merge-sort" for item in payload["presets"]))

    def test_get_preset(self) -> None:
        with build_client() as client:
            response = client.get("/api/v1/presets/recursive-fibonacci")
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["name"], "Recursive Fibonacci")
            self.assertEqual(payload["expected_complexity"], "O(2^n)")


if __name__ == "__main__":
    unittest.main()
