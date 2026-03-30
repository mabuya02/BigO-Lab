from __future__ import annotations

import unittest
from datetime import datetime, timezone

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


if __name__ == "__main__":
    unittest.main()
