from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from statistics import fmean
from typing import Iterable, Sequence

from app.core.runtime import cached_call
from app.core.settings import get_settings
from app.schemas.comparison import (
    ComparisonComplexityDelta,
    ComparisonComplexityInput,
    ComparisonHotspotComparison,
    ComparisonHotspotSummary,
    ComparisonRequest,
    ComparisonReport,
    ComparisonSummary,
    ComparisonSubjectInput,
    ComparisonSubjectSummary,
    ComparisonTrendDelta,
    ComparisonWinner,
)
from app.schemas.metrics import MetricPoint


@dataclass(frozen=True, slots=True)
class _TrendStats:
    start: float
    end: float
    growth_rate: float


class ComparisonService:
    COMPLEXITY_RANKS = {
        "o(1)": 0,
        "constant": 0,
        "o(log n)": 1,
        "logarithmic": 1,
        "o(n)": 2,
        "linear": 2,
        "o(n log n)": 3,
        "linearithmic": 3,
        "o(nlogn)": 3,
        "o(n^2)": 4,
        "quadratic": 4,
        "o(n^3)": 5,
        "cubic": 5,
        "o(2^n)": 6,
        "exponential": 6,
        "o(n!)": 7,
        "factorial": 7,
    }

    @classmethod
    def compare(cls, request: ComparisonRequest) -> ComparisonReport:
        settings = get_settings()

        def factory() -> dict:
            return cls._compare_uncached(request).model_dump()

        cached_payload, _ = cached_call(
            "comparisons",
            request.model_dump(mode="json"),
            ttl_seconds=settings.cache_analysis_ttl_seconds,
            factory=factory,
        )
        return ComparisonReport.model_validate(cached_payload)

    @classmethod
    def _compare_uncached(cls, request: ComparisonRequest) -> ComparisonReport:
        left = cls._summarize_subject(request.left)
        right = cls._summarize_subject(request.right)

        runtime = cls._compare_trend("runtime_ms", left.runtime_series, right.runtime_series)
        operations = cls._compare_trend("operations", left.operations_series, right.operations_series)
        complexity = cls._compare_complexity(left.complexity_estimate, right.complexity_estimate)
        hotspots = [
            cls._compare_hotspot("line", left.top_lines, right.top_lines),
            cls._compare_hotspot("function", left.top_functions, right.top_functions),
        ]

        overall_winner, confidence, tradeoffs = cls._compare_overall(runtime, operations, complexity, hotspots)
        verdict = cls._build_verdict(left.label, right.label, overall_winner, runtime, operations, complexity, tradeoffs)

        return ComparisonReport(
            left=left,
            right=right,
            runtime=runtime,
            operations=operations,
            complexity=complexity,
            hotspots=hotspots,
            summary=ComparisonSummary(
                overall_winner=overall_winner,
                confidence=confidence,
                verdict=verdict,
                tradeoffs=tradeoffs,
            ),
        )

    @dataclass(frozen=True, slots=True)
    class _PreparedSubject:
        label: str
        total_runs: int
        average_runtime_ms: float
        total_runtime_ms: float
        total_line_executions: int
        total_function_calls: int
        runtime_growth_rate: float
        operation_growth_rate: float
        dominant_line_number: int | None
        dominant_function_name: str | None
        complexity_estimate: ComparisonComplexityInput | None
        top_lines: list[ComparisonHotspotSummary]
        top_functions: list[ComparisonHotspotSummary]
        runtime_series: list[MetricPoint]
        operations_series: list[MetricPoint]

    @classmethod
    def _summarize_subject(cls, subject: ComparisonSubjectInput) -> _PreparedSubject:
        summary = subject.metrics.summary
        runtime_series = list(summary.runtime_series.points)
        operations_series = list(summary.operations_series.points)

        runtime_stats = cls._trend_stats(runtime_series)
        operation_stats = cls._trend_stats(operations_series)

        total_line_executions = int(summary.total_line_executions)
        total_function_calls = int(summary.total_function_calls)

        return cls._PreparedSubject(
            label=subject.label,
            total_runs=int(summary.total_runs),
            average_runtime_ms=float(summary.average_runtime_ms),
            total_runtime_ms=float(summary.total_runtime_ms),
            total_line_executions=total_line_executions,
            total_function_calls=total_function_calls,
            runtime_growth_rate=runtime_stats.growth_rate,
            operation_growth_rate=operation_stats.growth_rate,
            dominant_line_number=summary.dominant_line_number,
            dominant_function_name=summary.dominant_function_name,
            complexity_estimate=subject.complexity_estimate,
            top_lines=cls._top_line_hotspots(subject),
            top_functions=cls._top_function_hotspots(subject),
            runtime_series=runtime_series,
            operations_series=operations_series,
        )

    @classmethod
    def _top_line_hotspots(cls, subject: ComparisonSubjectInput, limit: int = 3) -> list[ComparisonHotspotSummary]:
        total = max(int(subject.metrics.summary.total_line_executions), 1)
        metrics = sorted(
            subject.metrics.line_metrics,
            key=lambda metric: (metric.total_execution_count, metric.total_time_ms, -metric.line_number),
            reverse=True,
        )[:limit]
        return [
            ComparisonHotspotSummary(
                kind="line",
                identifier=f"line {metric.line_number}",
                value=float(metric.total_execution_count),
                share_of_total=min(max(metric.total_execution_count / total, 0.0), 1.0),
            )
            for metric in metrics
        ]

    @classmethod
    def _top_function_hotspots(cls, subject: ComparisonSubjectInput, limit: int = 3) -> list[ComparisonHotspotSummary]:
        total = max(int(subject.metrics.summary.total_function_calls), 1)
        metrics = sorted(
            subject.metrics.function_metrics,
            key=lambda metric: (metric.total_call_count, metric.total_time_ms, metric.function_name),
            reverse=True,
        )[:limit]
        return [
            ComparisonHotspotSummary(
                kind="function",
                identifier=metric.function_name,
                value=float(metric.total_call_count),
                share_of_total=min(max(metric.total_call_count / total, 0.0), 1.0),
            )
            for metric in metrics
        ]

    @classmethod
    def _compare_trend(
        cls,
        metric_name: str,
        left_series: Sequence[MetricPoint],
        right_series: Sequence[MetricPoint],
    ) -> ComparisonTrendDelta:
        left_stats = cls._trend_stats(left_series)
        right_stats = cls._trend_stats(right_series)
        winner = cls._lower_is_better(left_stats.growth_rate, right_stats.growth_rate, left_stats.end, right_stats.end)
        delta = right_stats.end - left_stats.end
        percent_change = cls._percent_change(left_stats.end, right_stats.end)
        interpretation = cls._trend_interpretation(metric_name, left_stats, right_stats, winner)
        return ComparisonTrendDelta(
            metric_name=metric_name,
            left_start=left_stats.start,
            left_end=left_stats.end,
            right_start=right_stats.start,
            right_end=right_stats.end,
            left_growth_rate=left_stats.growth_rate,
            right_growth_rate=right_stats.growth_rate,
            delta=delta,
            percent_change=percent_change,
            winner=winner,
            interpretation=interpretation,
        )

    @classmethod
    def _compare_complexity(
        cls,
        left: ComparisonComplexityInput | None,
        right: ComparisonComplexityInput | None,
    ) -> ComparisonComplexityDelta:
        left_rank = cls._complexity_rank(left.estimated_class) if left is not None else None
        right_rank = cls._complexity_rank(right.estimated_class) if right is not None else None

        if left_rank is None and right_rank is None:
            return ComparisonComplexityDelta(
                left_class=None,
                right_class=None,
                left_rank=None,
                right_rank=None,
                delta=None,
                confidence_delta=None,
                winner="tie",
                interpretation="Neither side includes a complexity estimate.",
            )

        if left_rank is None:
            return ComparisonComplexityDelta(
                left_class=None,
                right_class=right.estimated_class if right else None,
                left_rank=None,
                right_rank=right_rank,
                delta=None,
                confidence_delta=None,
                winner="right",
                interpretation="Only the right side includes a complexity estimate.",
            )

        if right_rank is None:
            return ComparisonComplexityDelta(
                left_class=left.estimated_class if left else None,
                right_class=None,
                left_rank=left_rank,
                right_rank=None,
                delta=None,
                confidence_delta=None,
                winner="left",
                interpretation="Only the left side includes a complexity estimate.",
            )

        if left_rank == right_rank:
            confidence_delta = (left.confidence if left else 0.0) - (right.confidence if right else 0.0)
            winner = cls._confidence_winner(left.confidence if left else 0.0, right.confidence if right else 0.0)
            interpretation = (
                f"Both sides estimate {left.estimated_class if left else right.estimated_class}, "
                f"with confidence {left.confidence:.2f} vs {right.confidence:.2f}."
            )
            return ComparisonComplexityDelta(
                left_class=left.estimated_class if left else None,
                right_class=right.estimated_class if right else None,
                left_rank=left_rank,
                right_rank=right_rank,
                delta=0,
                confidence_delta=confidence_delta,
                winner=winner,
                interpretation=interpretation,
            )

        winner = "left" if left_rank < right_rank else "right"
        confidence_delta = (left.confidence if left else 0.0) - (right.confidence if right else 0.0)
        delta = right_rank - left_rank
        interpretation = (
            f"{'Left' if winner == 'left' else 'Right'} has the better asymptotic class "
            f"({left.estimated_class if winner == 'left' else right.estimated_class})."
        )
        return ComparisonComplexityDelta(
            left_class=left.estimated_class if left else None,
            right_class=right.estimated_class if right else None,
            left_rank=left_rank,
            right_rank=right_rank,
            delta=delta,
            confidence_delta=confidence_delta,
            winner=winner,
            interpretation=interpretation,
        )

    @classmethod
    def _compare_hotspot(
        cls,
        kind: str,
        left_hotspots: Sequence[ComparisonHotspotSummary],
        right_hotspots: Sequence[ComparisonHotspotSummary],
    ) -> ComparisonHotspotComparison:
        left_hotspot = left_hotspots[0] if left_hotspots else None
        right_hotspot = right_hotspots[0] if right_hotspots else None

        if left_hotspot is None and right_hotspot is None:
            return ComparisonHotspotComparison(
                kind=kind,  # type: ignore[arg-type]
                left_identifier=None,
                right_identifier=None,
                left_value=0.0,
                right_value=0.0,
                left_share_of_total=0.0,
                right_share_of_total=0.0,
                delta=0.0,
                winner="tie",
                interpretation=f"Neither side has {kind} hotspot data.",
            )

        if left_hotspot is None:
            return ComparisonHotspotComparison(
                kind=kind,  # type: ignore[arg-type]
                left_identifier=None,
                right_identifier=right_hotspot.identifier if right_hotspot else None,
                left_value=0.0,
                right_value=right_hotspot.value if right_hotspot else 0.0,
                left_share_of_total=0.0,
                right_share_of_total=right_hotspot.share_of_total if right_hotspot else 0.0,
                delta=right_hotspot.value if right_hotspot else 0.0,
                winner="right",
                interpretation=f"Only the right side has a {kind} hotspot to compare.",
            )

        if right_hotspot is None:
            return ComparisonHotspotComparison(
                kind=kind,  # type: ignore[arg-type]
                left_identifier=left_hotspot.identifier,
                right_identifier=None,
                left_value=left_hotspot.value,
                right_value=0.0,
                left_share_of_total=left_hotspot.share_of_total,
                right_share_of_total=0.0,
                delta=-left_hotspot.value,
                winner="left",
                interpretation=f"Only the left side has a {kind} hotspot to compare.",
            )

        winner = cls._lower_is_better(left_hotspot.value, right_hotspot.value, left_hotspot.value, right_hotspot.value)
        delta = right_hotspot.value - left_hotspot.value
        if kind == "line":
            interpretation = (
                f"Left's dominant line {left_hotspot.identifier} executes {left_hotspot.value:.0f} times "
                f"vs {right_hotspot.value:.0f} times on the right."
            )
        else:
            interpretation = (
                f"Left's dominant function {left_hotspot.identifier} is called {left_hotspot.value:.0f} times "
                f"vs {right_hotspot.value:.0f} times on the right."
            )
        return ComparisonHotspotComparison(
            kind=kind,  # type: ignore[arg-type]
            left_identifier=left_hotspot.identifier,
            right_identifier=right_hotspot.identifier,
            left_value=left_hotspot.value,
            right_value=right_hotspot.value,
            left_share_of_total=left_hotspot.share_of_total,
            right_share_of_total=right_hotspot.share_of_total,
            delta=delta,
            winner=winner,
            interpretation=interpretation,
        )

    @classmethod
    def _compare_overall(
        cls,
        runtime: ComparisonTrendDelta,
        operations: ComparisonTrendDelta,
        complexity: ComparisonComplexityDelta,
        hotspots: Sequence[ComparisonHotspotComparison],
    ) -> tuple[ComparisonWinner, float, list[str]]:
        left_score = 0.0
        right_score = 0.0
        tradeoffs: list[str] = []

        def apply(metric_name: str, winner: ComparisonWinner, weight: float) -> None:
            nonlocal left_score, right_score
            if winner == "left":
                left_score += weight
            elif winner == "right":
                right_score += weight
            else:
                left_score += weight / 2
                right_score += weight / 2

        apply("runtime", runtime.winner, 0.45)
        apply("operations", operations.winner, 0.3)
        apply("complexity", complexity.winner, 0.25)

        if runtime.winner != complexity.winner and runtime.winner != "tie" and complexity.winner != "tie":
            tradeoffs.append(
                f"Runtime favors {runtime.winner}, while asymptotic complexity favors {complexity.winner}."
            )
        if operations.winner != runtime.winner and operations.winner != "tie":
            tradeoffs.append(
                f"Operation growth favors {operations.winner}, which does not fully match the runtime trend."
            )
        for hotspot in hotspots:
            if hotspot.winner != "tie":
                tradeoffs.append(f"The {hotspot.kind} hotspot on the {hotspot.winner} side is lighter.")

        if abs(left_score - right_score) < 0.1:
            return "tie", 0.5, tradeoffs

        winner = "left" if left_score > right_score else "right"
        confidence = min(abs(left_score - right_score), 1.0)
        return winner, confidence, tradeoffs

    @staticmethod
    def _build_verdict(
        left_label: str,
        right_label: str,
        winner: ComparisonWinner,
        runtime: ComparisonTrendDelta,
        operations: ComparisonTrendDelta,
        complexity: ComparisonComplexityDelta,
        tradeoffs: Sequence[str],
    ) -> str:
        if winner == "tie":
            return f"{left_label} and {right_label} are closely matched in the measured range."

        preferred = left_label if winner == "left" else right_label
        other = right_label if winner == "left" else left_label
        lead = f"{preferred} is the better overall choice than {other}."
        if complexity.winner == winner and runtime.winner == winner:
            return f"{lead} It wins both the measured growth curve and the asymptotic estimate."
        if runtime.winner == winner and complexity.winner != winner:
            return f"{lead} It is faster on the measured range, but complexity leans the other way."
        if complexity.winner == winner and runtime.winner != winner:
            return f"{lead} It has the better asymptotic class, even though measured runtime is mixed."
        if tradeoffs:
            return f"{lead} The comparison shows tradeoffs across runtime, operations, and complexity."
        return lead

    @classmethod
    def _trend_stats(cls, points: Sequence[MetricPoint]) -> _TrendStats:
        normalized = cls._normalize_points(points)
        if not normalized:
            return _TrendStats(start=0.0, end=0.0, growth_rate=0.0)
        if len(normalized) == 1:
            value = normalized[0].value
            return _TrendStats(start=value, end=value, growth_rate=0.0)

        start = normalized[0].value
        end = normalized[-1].value
        growth_rate = cls._linear_regression_slope(normalized)
        return _TrendStats(start=start, end=end, growth_rate=growth_rate)

    @staticmethod
    def _normalize_points(points: Sequence[MetricPoint]) -> list[MetricPoint]:
        normalized = [
            MetricPoint(input_size=int(point.input_size), value=float(point.value))
            for point in points
            if isfinite(float(point.input_size)) and isfinite(float(point.value))
        ]
        normalized.sort(key=lambda point: point.input_size)
        return normalized

    @staticmethod
    def _linear_regression_slope(points: Sequence[MetricPoint]) -> float:
        if len(points) < 2:
            return 0.0
        xs = [float(point.input_size) for point in points]
        ys = [float(point.value) for point in points]
        mean_x = fmean(xs)
        mean_y = fmean(ys)
        numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
        denominator = sum((x - mean_x) ** 2 for x in xs)
        return numerator / denominator if denominator else 0.0

    @staticmethod
    def _lower_is_better(left_value: float, right_value: float, left_tiebreak: float, right_tiebreak: float) -> ComparisonWinner:
        if abs(left_value - right_value) >= 1e-9:
            return "left" if left_value < right_value else "right"
        if abs(left_tiebreak - right_tiebreak) < 1e-9:
            return "tie"
        return "left" if left_tiebreak < right_tiebreak else "right"

    @staticmethod
    def _confidence_winner(left_confidence: float, right_confidence: float) -> ComparisonWinner:
        if abs(left_confidence - right_confidence) < 1e-9:
            return "tie"
        return "left" if left_confidence > right_confidence else "right"

    @staticmethod
    def _percent_change(left_value: float, right_value: float) -> float:
        if abs(left_value) < 1e-9:
            return 0.0
        return (right_value - left_value) / abs(left_value)

    @classmethod
    def _complexity_rank(cls, value: str) -> int:
        normalized = value.strip().lower().replace(" ", "")
        if normalized in cls.COMPLEXITY_RANKS:
            return cls.COMPLEXITY_RANKS[normalized]
        if "!" in normalized:
            return 7
        if "2^n" in normalized or "exponential" in normalized:
            return 6
        if "n^3" in normalized or "cubic" in normalized:
            return 5
        if "n^2" in normalized or "quadratic" in normalized:
            return 4
        if "nlogn" in normalized or "nlog(n)" in normalized or "linearithmic" in normalized:
            return 3
        if normalized in {"n", "linear"}:
            return 2
        if "logn" in normalized or "logarithmic" in normalized:
            return 1
        if normalized in {"1", "o(1)", "constant"}:
            return 0
        return 99

    @classmethod
    def _trend_interpretation(
        cls,
        metric_name: str,
        left: _TrendStats,
        right: _TrendStats,
        winner: ComparisonWinner,
    ) -> str:
        if winner == "tie":
            return (
                f"Both sides have similar {metric_name} growth across the measured range "
                f"({left.start:.2f} -> {left.end:.2f} vs {right.start:.2f} -> {right.end:.2f})."
            )
        preferred = "left" if winner == "left" else "right"
        preferred_stats = left if winner == "left" else right
        other_stats = right if winner == "left" else left
        return (
            f"{preferred.title()} grows more slowly for {metric_name}: "
            f"{preferred_stats.start:.2f} -> {preferred_stats.end:.2f} versus "
            f"{other_stats.start:.2f} -> {other_stats.end:.2f}."
        )
