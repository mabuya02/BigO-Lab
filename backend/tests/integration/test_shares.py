from __future__ import annotations

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.shares import router as shares_router


def build_client() -> TestClient:
    app = FastAPI()
    app.include_router(shares_router, prefix="/api/v1")
    return TestClient(app)


class ShareApiTests(unittest.TestCase):
    def test_create_and_resolve_share(self) -> None:
        with build_client() as client:
            created_response = client.post(
                "/api/v1/shares",
                json={
                    "kind": "experiment-result",
                    "label": "merge-sort-compare",
                    "data": {
                        "code": "print('hello')",
                        "runtime_ms": 42,
                        "metrics": {"lines": {"12": 8}},
                    },
                    "expires_in_seconds": 3600,
                },
            )
            self.assertEqual(created_response.status_code, 201)
            created = created_response.json()
            self.assertIn("token", created)

            resolved_response = client.post(
                "/api/v1/shares/resolve",
                json={"token": created["token"]},
            )
            self.assertEqual(resolved_response.status_code, 200)
            resolved = resolved_response.json()
            self.assertEqual(resolved["label"], "merge-sort-compare")
            self.assertEqual(resolved["data"]["runtime_ms"], 42)


if __name__ == "__main__":
    unittest.main()
