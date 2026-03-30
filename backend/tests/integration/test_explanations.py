from __future__ import annotations

import unittest
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api.routes import explanations
from app.main import create_app
from app.schemas.complexity import ComplexityEstimateRead, ComplexityFitRead
from tests.helpers import reset_database


class ExplanationApiTests(unittest.TestCase):
    def test_generate_explanation(self) -> None:
        reset_database()
        app = create_app()
        app.include_router(explanations.router, prefix="/api/v1")

        payload = {
            "metrics_snapshot": {
                "summary": {
                    "total_runs": 4,
                    "input_sizes": [10, 20, 40, 80],
                    "average_runtime_ms": 269.0,
                    "min_runtime_ms": 15.0,
                    "max_runtime_ms": 805.0,
                    "total_runtime_ms": 1076.0,
                    "total_line_executions": 760,
                    "total_function_calls": 1,
                    "dominant_line_number": 12,
                    "dominant_function_name": "bubble_sort",
                    "runtime_series": {
                        "label": "runtime_ms",
                        "points": [
                            {"input_size": 10, "value": 15.0},
                            {"input_size": 20, "value": 55.0},
                            {"input_size": 40, "value": 205.0},
                            {"input_size": 80, "value": 805.0},
                        ],
                    },
                    "operations_series": {"label": "operations", "points": []},
                },
                "line_metrics": [
                    {
                        "line_number": 12,
                        "total_execution_count": 640,
                        "total_time_ms": 420.0,
                        "average_time_ms": 0.65625,
                        "percentage_of_total": 0.72,
                        "nesting_depth": 2,
                        "loop_iterations": 640,
                        "branch_visits": 0,
                    }
                ],
                "function_metrics": [
                    {
                        "function_name": "bubble_sort",
                        "qualified_name": "bubble_sort",
                        "total_call_count": 1,
                        "total_time_ms": 510.0,
                        "average_time_ms": 510.0,
                        "self_time_ms": 500.0,
                        "max_depth": 1,
                        "is_recursive": False,
                    }
                ],
            },
            "complexity_estimate": {
                "id": "ce-1",
                "experiment_id": None,
                "metric_name": "runtime_ms",
                "estimated_class": "O(n^2)",
                "confidence": 0.91,
                "sample_count": 4,
                "explanation": "Quadratic growth fits nested loop behavior.",
                "alternatives": [
                    {
                        "label": "linear",
                        "big_o": "O(n)",
                        "quality": 0.4,
                        "rmse": 12.0,
                        "normalized_rmse": 0.4,
                        "slope": 1.0,
                        "intercept": 0.0,
                        "valid": True,
                        "notes": "Lower fit quality",
                    }
                ],
                "evidence": {"source": "integration-test"},
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            "max_sections": 5,
        }

        with TestClient(app) as client:
            response = client.post("/api/v1/explanations/generate", json=payload)

            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertEqual(body["dominant_line_number"], 12)
            self.assertEqual(body["dominant_function_name"], "bubble_sort")
            self.assertEqual(body["complexity_class"], "O(n^2)")
            self.assertTrue(any(section["kind"] == "loop" for section in body["sections"]))
            self.assertIsInstance(body["caveats"], list)
