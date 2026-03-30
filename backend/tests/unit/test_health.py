from __future__ import annotations

import unittest

from tests.helpers import get_client


class HealthApiTests(unittest.TestCase):
    def test_health_endpoints(self) -> None:
        with get_client() as client:
            live_response = client.get("/api/v1/health/live")
            self.assertEqual(live_response.status_code, 200)
            self.assertEqual(live_response.json()["status"], "ok")

            ready_response = client.get("/api/v1/health/ready")
            self.assertEqual(ready_response.status_code, 200)
            self.assertIn(ready_response.json()["status"], {"ok", "degraded"})
