from __future__ import annotations

import unittest

from app.schemas.comparison import ComparisonComplexityInput, ComparisonRequest, ComparisonSubjectInput
from app.schemas.metrics import (
    AggregatedFunctionMetric,
    AggregatedLineMetric,
    ExperimentMetricsSnapshot,
    MetricPoint,
    MetricSeries,
    MetricSummary,
)
from app.services.comparison_service import ComparisonService


def build_snapshot(
    *,
    label: str,
    runtime_points: list[tuple[int, float]],
    operation_points: list[tuple[int, float]],
    line_metrics: list[tuple[int, int, float]],
    function_metrics: list[tuple[str, int, float]],
    dominant_line_number: int | None,
    dominant_function_name: str | None,
) -> ExperimentMetricsSnapshot:
    summary = MetricSummary(
        total_runs=len(runtime_points),
        input_sizes=[size for size, _ in runtime_points],
        average_runtime_ms=sum(value for _, value in runtime_points) / max(len(runtime_points), 1),
        min_runtime_ms=min(value for _, value in runtime_points),
        max_runtime_ms=max(value for _, value in runtime_points),
        total_runtime_ms=sum(value for _, value in runtime_points),
        total_line_executions=int(sum(value for _, value in operation_points)),
        total_function_calls=int(sum(count for _, count, _ in function_metrics)),
        dominant_line_number=dominant_line_number,
        dominant_function_name=dominant_function_name,
        runtime_series=MetricSeries(
            label="runtime_ms",
            points=[MetricPoint(input_size=size, value=value) for size, value in runtime_points],
        ),
        operations_series=MetricSeries(
            label="operations",
            points=[MetricPoint(input_size=size, value=value) for size, value in operation_points],
        ),
    )
    return ExperimentMetricsSnapshot(
        summary=summary,
        line_metrics=[
            AggregatedLineMetric(
                line_number=line_number,
                total_execution_count=execution_count,
                total_time_ms=total_time_ms,
                average_time_ms=total_time_ms / max(execution_count, 1),
                percentage_of_total=execution_count / max(summary.total_line_executions, 1),
                nesting_depth=1,
                loop_iterations=execution_count,
                branch_visits=0,
            )
            for line_number, execution_count, total_time_ms in line_metrics
        ],
        function_metrics=[
            AggregatedFunctionMetric(
                function_name=function_name,
                qualified_name=function_name,
                total_call_count=call_count,
                total_time_ms=total_time_ms,
                average_time_ms=total_time_ms / max(call_count, 1),
                self_time_ms=total_time_ms,
                max_depth=1,
                is_recursive=False,
            )
            for function_name, call_count, total_time_ms in function_metrics
        ],
    )


class ComparisonServiceTests(unittest.TestCase):
    def test_compare_prefers_faster_lower_growth_and_better_complexity(self) -> None:
        left = build_snapshot(
            label="linear-search",
            runtime_points=[(10, 1.0), (100, 2.0), (1000, 4.0)],
            operation_points=[(10, 10), (100, 100), (1000, 1000)],
            line_metrics=[(12, 60, 0.0), (8, 20, 0.0)],
            function_metrics=[("linear_search", 15, 0.0)],
            dominant_line_number=12,
            dominant_function_name="linear_search",
        )
        right = build_snapshot(
            label="nested-loop",
            runtime_points=[(10, 1.2), (100, 4.5), (1000, 20.0)],
            operation_points=[(10, 30), (100, 300), (1000, 3000)],
            line_metrics=[(21, 300, 0.0), (22, 150, 0.0)],
            function_metrics=[("nested_loop", 45, 0.0)],
            dominant_line_number=21,
            dominant_function_name="nested_loop",
        )

        report = ComparisonService.compare(
            ComparisonRequest(
                left=ComparisonSubjectInput(
                    label="linear-search",
                    metrics=left,
                    complexity_estimate=ComparisonComplexityInput(
                        estimated_class="O(n)",
                        confidence=0.84,
                        sample_count=3,
                        explanation="linear growth",
                    ),
                ),
                right=ComparisonSubjectInput(
                    label="nested-loop",
                    metrics=right,
                    complexity_estimate=ComparisonComplexityInput(
                        estimated_class="O(n^2)",
                        confidence=0.91,
                        sample_count=3,
                        explanation="quadratic growth",
                    ),
                ),
            )
        )

        self.assertEqual(report.summary.overall_winner, "left")
        self.assertEqual(report.runtime.winner, "left")
        self.assertEqual(report.operations.winner, "left")
        self.assertEqual(report.complexity.winner, "left")
        self.assertEqual(report.hotspots[0].kind, "line")
        self.assertEqual(report.hotspots[1].kind, "function")
        self.assertIn("better overall choice", report.summary.verdict)

    def test_compare_handles_tight_tie_with_missing_complexity(self) -> None:
        left = build_snapshot(
            label="variant-a",
            runtime_points=[(10, 10.0), (100, 11.0)],
            operation_points=[(10, 100), (100, 110)],
            line_metrics=[(3, 10, 0.0)],
            function_metrics=[("a", 2, 0.0)],
            dominant_line_number=3,
            dominant_function_name="a",
        )
        right = build_snapshot(
            label="variant-b",
            runtime_points=[(10, 10.0), (100, 11.1)],
            operation_points=[(10, 100), (100, 111)],
            line_metrics=[(4, 9, 0.0)],
            function_metrics=[("b", 2, 0.0)],
            dominant_line_number=4,
            dominant_function_name="b",
        )

        report = ComparisonService.compare(
            ComparisonRequest(
                left=ComparisonSubjectInput(label="variant-a", metrics=left),
                right=ComparisonSubjectInput(label="variant-b", metrics=right),
            )
        )

        self.assertIn(report.summary.overall_winner, {"left", "right", "tie"})
        self.assertEqual(report.complexity.winner, "tie")
        self.assertIsNone(report.left.complexity_estimate)
        self.assertEqual(report.hotspots[0].kind, "line")
        self.assertEqual(report.hotspots[1].kind, "function")
