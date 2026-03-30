from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from statistics import mean
from typing import Any, Iterable, Sequence

from app.schemas.metrics import (
    AggregatedFunctionMetric,
    AggregatedLineMetric,
    ExperimentMetricsSnapshot,
    MetricPoint,
    MetricSeries,
    MetricSummary,
)


def _get_value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _to_int(value: Any) -> int:
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


@dataclass(slots=True)
class AggregationContext:
    runs: list[Any] = field(default_factory=list)
    line_metrics: list[Any] = field(default_factory=list)
    function_metrics: list[Any] = field(default_factory=list)


def aggregate_line_metrics(metrics: Iterable[Any]) -> list[AggregatedLineMetric]:
    grouped: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    nesting_depths: dict[int, int] = {}
    sample_counts: dict[int, int] = defaultdict(int)

    for metric in metrics:
        line_number = _to_int(_get_value(metric, "line_number"))
        grouped[line_number]["total_execution_count"] += _to_int(_get_value(metric, "execution_count"))
        grouped[line_number]["total_time_ms"] += _to_float(_get_value(metric, "total_time_ms"))
        grouped[line_number]["percentage_of_total"] += _to_float(_get_value(metric, "percentage_of_total"))
        grouped[line_number]["loop_iterations"] += _to_int(_get_value(metric, "loop_iterations"))
        grouped[line_number]["branch_visits"] += _to_int(_get_value(metric, "branch_visits"))
        nesting_depths[line_number] = max(nesting_depths.get(line_number, 0), _to_int(_get_value(metric, "nesting_depth")))
        sample_counts[line_number] += 1

    results: list[AggregatedLineMetric] = []
    for line_number, values in sorted(grouped.items()):
        total_execution_count = int(values["total_execution_count"])
        total_time_ms = values["total_time_ms"]
        results.append(
            AggregatedLineMetric(
                line_number=line_number,
                total_execution_count=total_execution_count,
                total_time_ms=total_time_ms,
                average_time_ms=(total_time_ms / total_execution_count) if total_execution_count else 0.0,
                percentage_of_total=(values["percentage_of_total"] / sample_counts.get(line_number, 1))
                if sample_counts.get(line_number, 0)
                else 0.0,
                nesting_depth=nesting_depths.get(line_number, 0),
                loop_iterations=int(values["loop_iterations"]),
                branch_visits=int(values["branch_visits"]),
            )
        )
    return results


def aggregate_function_metrics(metrics: Iterable[Any]) -> list[AggregatedFunctionMetric]:
    grouped: dict[str, dict[str, Any]] = {}

    for metric in metrics:
        function_name = str(_get_value(metric, "function_name", "")).strip()
        if not function_name:
            continue
        entry = grouped.setdefault(
            function_name,
            {
                "qualified_name": _get_value(metric, "qualified_name"),
                "total_call_count": 0,
                "total_time_ms": 0.0,
                "self_time_ms": 0.0,
                "max_depth": 0,
                "is_recursive": False,
            },
        )
        entry["total_call_count"] += _to_int(_get_value(metric, "call_count"))
        entry["total_time_ms"] += _to_float(_get_value(metric, "total_time_ms"))
        entry["self_time_ms"] += _to_float(_get_value(metric, "self_time_ms"))
        entry["max_depth"] = max(entry["max_depth"], _to_int(_get_value(metric, "max_depth")))
        entry["is_recursive"] = entry["is_recursive"] or bool(_get_value(metric, "is_recursive"))
        qualified_name = _get_value(metric, "qualified_name")
        if qualified_name:
            entry["qualified_name"] = qualified_name

    results: list[AggregatedFunctionMetric] = []
    for function_name, values in sorted(grouped.items()):
        total_call_count = int(values["total_call_count"])
        total_time_ms = float(values["total_time_ms"])
        results.append(
            AggregatedFunctionMetric(
                function_name=function_name,
                qualified_name=values["qualified_name"],
                total_call_count=total_call_count,
                total_time_ms=total_time_ms,
                average_time_ms=(total_time_ms / total_call_count) if total_call_count else 0.0,
                self_time_ms=float(values["self_time_ms"]),
                max_depth=int(values["max_depth"]),
                is_recursive=bool(values["is_recursive"]),
            )
        )
    return results


def aggregate_runs(runs: Sequence[Any]) -> MetricSummary:
    runtimes: list[float] = []
    input_sizes: list[int] = []
    total_line_executions = 0
    total_function_calls = 0
    dominant_line_number: int | None = None
    dominant_line_total = -1.0
    dominant_function_name: str | None = None
    dominant_function_total = -1.0

    for run in runs:
        runtime = _to_float(_get_value(run, "runtime_ms"))
        input_size = _to_int(_get_value(run, "input_size"))
        runtimes.append(runtime)
        input_sizes.append(input_size)

        run_line_metrics = list(_get_value(run, "line_metrics", []) or [])
        run_function_metrics = list(_get_value(run, "function_metrics", []) or [])

        for line_metric in run_line_metrics:
            execution_count = _to_int(_get_value(line_metric, "execution_count"))
            total_line_executions += execution_count
            total_time_ms = _to_float(_get_value(line_metric, "total_time_ms"))
            if total_time_ms > dominant_line_total:
                dominant_line_total = total_time_ms
                dominant_line_number = _to_int(_get_value(line_metric, "line_number"))

        for function_metric in run_function_metrics:
            call_count = _to_int(_get_value(function_metric, "call_count"))
            total_function_calls += call_count
            total_time_ms = _to_float(_get_value(function_metric, "total_time_ms"))
            if total_time_ms > dominant_function_total:
                dominant_function_total = total_time_ms
                dominant_function_name = str(_get_value(function_metric, "function_name"))

    runtime_points = [
        MetricPoint(input_size=input_size, value=runtime)
        for input_size, runtime in sorted(zip(input_sizes, runtimes), key=lambda item: item[0])
    ]
    operation_points = [
        MetricPoint(
            input_size=_to_int(_get_value(run, "input_size")),
            value=sum(_to_int(_get_value(metric, "execution_count")) for metric in _get_value(run, "line_metrics", []) or []),
        )
        for run in runs
    ]
    operation_points.sort(key=lambda point: point.input_size)

    return MetricSummary(
        total_runs=len(runs),
        input_sizes=sorted(input_sizes),
        average_runtime_ms=mean(runtimes) if runtimes else 0.0,
        min_runtime_ms=min(runtimes) if runtimes else 0.0,
        max_runtime_ms=max(runtimes) if runtimes else 0.0,
        total_runtime_ms=sum(runtimes),
        total_line_executions=total_line_executions,
        total_function_calls=total_function_calls,
        dominant_line_number=dominant_line_number,
        dominant_function_name=dominant_function_name,
        runtime_series=MetricSeries(label="runtime_ms", points=runtime_points),
        operations_series=MetricSeries(label="operations", points=operation_points),
    )


def build_experiment_metrics_snapshot(runs: Sequence[Any]) -> ExperimentMetricsSnapshot:
    line_metrics = aggregate_line_metrics(
        metric
        for run in runs
        for metric in (_get_value(run, "line_metrics", []) or [])
    )
    function_metrics = aggregate_function_metrics(
        metric
        for run in runs
        for metric in (_get_value(run, "function_metrics", []) or [])
    )
    return ExperimentMetricsSnapshot(
        summary=aggregate_runs(runs),
        line_metrics=line_metrics,
        function_metrics=function_metrics,
    )
