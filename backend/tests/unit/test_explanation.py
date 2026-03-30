from __future__ import annotations

import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import httpx

from app.core.runtime import reset_runtime_state
from app.core.settings import get_settings
from app.schemas.complexity import ComplexityEstimateRead, ComplexityFitRead
from app.schemas.explanation import ExplanationRequest
from app.schemas.metrics import (
    AggregatedFunctionMetric,
    AggregatedLineMetric,
    ExperimentMetricsSnapshot,
    MetricPoint,
    MetricSeries,
    MetricSummary,
)
from app.services.explanation_service import ExplanationService


def build_snapshot(
    *,
    runtime_points: list[tuple[int, float]],
    line_metrics: list[AggregatedLineMetric] | None = None,
    function_metrics: list[AggregatedFunctionMetric] | None = None,
) -> ExperimentMetricsSnapshot:
    points = [MetricPoint(input_size=size, value=value) for size, value in runtime_points]
    summary = MetricSummary(
        total_runs=len(points),
        input_sizes=[point.input_size for point in points],
        average_runtime_ms=sum(point.value for point in points) / len(points),
        min_runtime_ms=min(point.value for point in points),
        max_runtime_ms=max(point.value for point in points),
        total_runtime_ms=sum(point.value for point in points),
        total_line_executions=sum(metric.total_execution_count for metric in line_metrics or []),
        total_function_calls=sum(metric.total_call_count for metric in function_metrics or []),
        dominant_line_number=(line_metrics[0].line_number if line_metrics else None),
        dominant_function_name=(function_metrics[0].function_name if function_metrics else None),
        runtime_series=MetricSeries(label="runtime_ms", points=points),
        operations_series=MetricSeries(label="operations", points=[]),
    )
    return ExperimentMetricsSnapshot(
        summary=summary,
        line_metrics=line_metrics or [],
        function_metrics=function_metrics or [],
    )


class ExplanationServiceTests(unittest.TestCase):
    def tearDown(self) -> None:
        os.environ.pop("EXPLANATION_PROVIDER", None)
        os.environ.pop("OLLAMA_API_KEY", None)
        os.environ.pop("OLLAMA_MODEL", None)
        os.environ.pop("EXPLANATION_ALLOW_FALLBACK", None)
        get_settings.cache_clear()
        reset_runtime_state()

    def test_identifies_dominant_loop_and_quadratic_signal(self) -> None:
        snapshot = build_snapshot(
            runtime_points=[(10, 15), (20, 55), (40, 205), (80, 805)],
            line_metrics=[
                AggregatedLineMetric(
                    line_number=12,
                    total_execution_count=640,
                    total_time_ms=420.0,
                    average_time_ms=0.65625,
                    percentage_of_total=0.72,
                    nesting_depth=2,
                    loop_iterations=640,
                    branch_visits=0,
                ),
                AggregatedLineMetric(
                    line_number=8,
                    total_execution_count=120,
                    total_time_ms=40.0,
                    average_time_ms=0.3333,
                    percentage_of_total=0.14,
                    nesting_depth=0,
                    loop_iterations=0,
                    branch_visits=0,
                ),
            ],
            function_metrics=[
                AggregatedFunctionMetric(
                    function_name="bubble_sort",
                    qualified_name="bubble_sort",
                    total_call_count=1,
                    total_time_ms=510.0,
                    average_time_ms=510.0,
                    self_time_ms=500.0,
                    max_depth=1,
                    is_recursive=False,
                )
            ],
        )
        estimate = ComplexityEstimateRead(
            id="ce-1",
            experiment_id=None,
            metric_name="runtime_ms",
            estimated_class="O(n^2)",
            confidence=0.91,
            sample_count=4,
            explanation="Quadratic growth fits nested loop behavior.",
            alternatives=[
                ComplexityFitRead(
                    label="linear",
                    big_o="O(n)",
                    quality=0.4,
                    rmse=12.0,
                    normalized_rmse=0.4,
                    slope=1.0,
                    intercept=0.0,
                    valid=True,
                    notes="Lower fit quality",
                )
            ],
            evidence={"source": "unit-test"},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        response = ExplanationService.generate(
            ExplanationRequest(metrics_snapshot=snapshot, complexity_estimate=estimate)
        )

        self.assertIn("faster than linear", response.headline)
        self.assertEqual(response.dominant_line_number, 12)
        self.assertEqual(response.dominant_function_name, "bubble_sort")
        self.assertEqual(response.complexity_class, "O(n^2)")
        self.assertTrue(any(section.kind == "loop" for section in response.sections))
        self.assertTrue(any("nested loops" in section.body or "repeated work" in section.body for section in response.sections))

    def test_adds_caveats_for_sparse_data(self) -> None:
        snapshot = build_snapshot(runtime_points=[(10, 10), (20, 18)])

        response = ExplanationService.generate(ExplanationRequest(metrics_snapshot=snapshot))

        self.assertTrue(any("small number of runtime samples" in caveat for caveat in response.caveats))
        self.assertTrue(any(section.kind == "caveat" for section in response.sections))
        self.assertIsNone(response.complexity_class)

    def test_uses_ollama_cloud_when_enabled(self) -> None:
        os.environ["EXPLANATION_PROVIDER"] = "ollama_cloud"
        os.environ["OLLAMA_API_KEY"] = "test-key"
        os.environ["OLLAMA_MODEL"] = "gpt-oss:120b"
        get_settings.cache_clear()
        reset_runtime_state()

        snapshot = build_snapshot(runtime_points=[(16, 12), (32, 21), (64, 33)])
        request = ExplanationRequest(metrics_snapshot=snapshot)

        cloud_response = {
            "headline": "Mocked cloud explanation",
            "summary": "This explanation came from Ollama Cloud.",
            "complexity_class": "O(n)",
            "confidence": 0.82,
            "dominant_line_number": None,
            "dominant_function_name": None,
            "sections": [
                {
                    "kind": "summary",
                    "title": "Cloud summary",
                    "body": "Structured output from the mocked cloud provider.",
                    "evidence": ["provider=ollama_cloud"],
                }
            ],
            "caveats": [],
        }

        with patch(
            "app.integrations.ollama_cloud.httpx.post",
            return_value=_FakeHttpResponse({"message": {"content": _json_dump(cloud_response)}}),
        ):
            response = ExplanationService.generate(request)

        self.assertEqual(response.headline, "Mocked cloud explanation")
        self.assertEqual(response.complexity_class, "O(n)")
        self.assertEqual(response.sections[0].title, "Cloud summary")

    def test_falls_back_to_heuristics_when_ollama_cloud_fails(self) -> None:
        os.environ["EXPLANATION_PROVIDER"] = "ollama_cloud"
        os.environ["OLLAMA_API_KEY"] = "test-key"
        os.environ["OLLAMA_MODEL"] = "gpt-oss:120b"
        os.environ["EXPLANATION_ALLOW_FALLBACK"] = "true"
        get_settings.cache_clear()
        reset_runtime_state()

        snapshot = build_snapshot(runtime_points=[(8, 10), (16, 40), (32, 160)])
        request = ExplanationRequest(metrics_snapshot=snapshot)

        with patch("app.integrations.ollama_cloud.httpx.post", side_effect=httpx.ConnectError("network down")):
            response = ExplanationService.generate(request)

        self.assertTrue(response.headline)
        self.assertTrue(any("fell back to the local heuristic generator" in caveat for caveat in response.caveats))
        self.assertTrue(any(section.kind == "caveat" for section in response.sections))


def _json_dump(payload: dict) -> str:
    import json

    return json.dumps(payload)


class _FakeHttpResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


if __name__ == "__main__":
    unittest.main()
