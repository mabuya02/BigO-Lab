from __future__ import annotations

import unittest

from tests.helpers import get_client


class PresetApiTests(unittest.TestCase):
    def test_list_presets(self) -> None:
        with get_client() as client:
            response = client.get("/api/v1/presets")
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertIn("presets", payload)
            self.assertTrue(any(item["slug"] == "merge-sort" for item in payload["presets"]))

    def test_get_preset(self) -> None:
        with get_client() as client:
            response = client.get("/api/v1/presets/recursive-fibonacci")
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["name"], "Recursive Fibonacci")
            self.assertEqual(payload["expected_complexity"], "O(2^n)")
