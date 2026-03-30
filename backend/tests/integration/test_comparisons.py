from __future__ import annotations

import unittest

from tests.unit.test_comparison import build_snapshot
from tests.helpers import get_client


class ComparisonApiTests(unittest.TestCase):
    def test_compare_route_returns_structured_report(self) -> None:
        left = build_snapshot(
            label="bubble-sort",
            runtime_points=[(10, 2.0), (100, 20.0)],
            operation_points=[(10, 30), (100, 300)],
            line_metrics=[(12, 90, 0.0), (13, 60, 0.0)],
            function_metrics=[("bubble_sort", 18, 0.0)],
            dominant_line_number=12,
            dominant_function_name="bubble_sort",
        )
        right = build_snapshot(
            label="merge-sort",
            runtime_points=[(10, 1.2), (100, 5.0)],
            operation_points=[(10, 12), (100, 60)],
            line_metrics=[(21, 18, 0.0), (22, 10, 0.0)],
            function_metrics=[("merge_sort", 6, 0.0)],
            dominant_line_number=21,
            dominant_function_name="merge_sort",
        )

        with get_client() as client:
            response = client.post(
                "/api/v1/comparisons/compare",
                json={
                    "left": {
                        "label": "bubble-sort",
                        "metrics": left.model_dump(),
                        "complexity_estimate": {
                            "estimated_class": "O(n^2)",
                            "confidence": 0.93,
                            "sample_count": 2,
                            "explanation": "quadratic growth",
                            "evidence": {"source": "test"},
                        },
                    },
                    "right": {
                        "label": "merge-sort",
                        "metrics": right.model_dump(),
                        "complexity_estimate": {
                            "estimated_class": "O(n log n)",
                            "confidence": 0.95,
                            "sample_count": 2,
                            "explanation": "linearithmic growth",
                            "evidence": {"source": "test"},
                        },
                    },
                },
            )

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["summary"]["overall_winner"], "right")
            self.assertEqual(payload["runtime"]["winner"], "right")
            self.assertEqual(payload["operations"]["winner"], "right")
            self.assertEqual(payload["complexity"]["winner"], "right")
            self.assertEqual(payload["hotspots"][0]["kind"], "line")
            self.assertEqual(payload["hotspots"][1]["kind"], "function")
