from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.core.performance import measure
from app.experiments.aggregator import build_experiment_metrics_snapshot
from app.experiments.input_generator import InputGenerator, InputKind, InputProfile
from app.schemas.complexity import ComplexityEstimateRead
from app.schemas.common import APIModel
from app.schemas.execution import (
    CodeExecutionRequest,
    CodeExecutionResult,
    ExecutionBackend,
    ExecutionBackendStatus,
)
from app.services.complexity_service import ComplexityService
from app.schemas.metrics import ExperimentMetricsSnapshot, FunctionMetricCreate, LineMetricCreate
from app.services.execution_service import ExecutionService


def _compute_loop_nesting(code: str) -> dict[int, int]:
    """Walk the AST and compute the loop nesting depth for every line."""
    nesting: dict[int, int] = {}
    try:
        tree = __import__("ast").parse(code)
    except SyntaxError:
        return nesting

    def _walk(node: object, depth: int = 0) -> None:
        import ast as _ast

        if not isinstance(node, _ast.AST):
            return

        is_loop = isinstance(node, (_ast.For, _ast.While))
        child_depth = depth + 1 if is_loop else depth

        if hasattr(node, "lineno"):
            line = node.lineno
            nesting[line] = max(nesting.get(line, 0), depth if not is_loop else child_depth)

        for child in _ast.iter_child_nodes(node):
            _walk(child, child_depth if is_loop else depth)

    _walk(tree)
    return nesting


def _build_line_metrics_from_instrumentation(
    execution_result: CodeExecutionResult,
    code: str = "",
) -> list[LineMetricCreate]:
    instrumentation = execution_result.instrumentation
    if instrumentation is None:
        return []

    loop_nesting = _compute_loop_nesting(code) if code else {}

    loop_iterations_by_line: dict[int, int] = {}
    for loop_key, count in instrumentation.loop_iteration_counts.items():
        _, _, line_fragment = loop_key.rpartition("@")
        line_number_raw = line_fragment.split(":", 1)[0]
        try:
            line_number = int(line_number_raw)
        except ValueError:
            continue
        loop_iterations_by_line[line_number] = loop_iterations_by_line.get(line_number, 0) + int(count)

    total_line_executions = sum(instrumentation.line_counts.values()) or 1
    metrics: list[LineMetricCreate] = []
    for line_number in instrumentation.line_numbers:
        execution_count = int(instrumentation.line_counts.get(line_number, 0))
        metrics.append(
            LineMetricCreate(
                line_number=line_number,
                execution_count=execution_count,
                total_time_ms=0.0,
                percentage_of_total=execution_count / total_line_executions,
                nesting_depth=loop_nesting.get(line_number, 0),
                loop_iterations=loop_iterations_by_line.get(line_number, 0),
                branch_visits=0,
            )
        )
    return metrics


def _build_function_metrics_from_instrumentation(
    execution_result: CodeExecutionResult,
) -> list[FunctionMetricCreate]:
    instrumentation = execution_result.instrumentation
    if instrumentation is None:
        return []

    metrics: list[FunctionMetricCreate] = []
    for qualified_name, count in sorted(instrumentation.function_call_counts.items()):
        function_name = qualified_name.split(".")[-1]
        metrics.append(
            FunctionMetricCreate(
                function_name=function_name,
                qualified_name=qualified_name,
                call_count=int(count),
                total_time_ms=0.0,
                self_time_ms=0.0,
                max_depth=max(qualified_name.count("."), 0),
                is_recursive=False,
            )
        )
    return metrics


class PlaygroundRunResponse(APIModel):
    code: str
    input: str
    backend_requested: ExecutionBackend
    instrumented: bool
    execution: CodeExecutionResult


class PlaygroundExperimentRun(APIModel):
    input_size: int
    repetition_index: int
    input_kind: InputKind
    input_profile: InputProfile
    generated_input: dict[str, Any]
    execution: CodeExecutionResult


class PlaygroundExperimentResponse(APIModel):
    code: str
    backend_requested: ExecutionBackend
    instrumented: bool
    input_kind: InputKind
    input_profile: InputProfile
    repetitions: int
    runs: list[PlaygroundExperimentRun]
    metrics_snapshot: ExperimentMetricsSnapshot
    complexity_estimate: ComplexityEstimateRead | None = None
    operations_complexity_estimate: ComplexityEstimateRead | None = None
    orchestration_runtime_ms: float = 0.0


class PlaygroundStatusResponse(APIModel):
    mode: str
    description: str
    backend_status: ExecutionBackendStatus


class PlaygroundService:
    @staticmethod
    def run_code(
        *,
        code: str,
        input_text: str = "",
        backend: ExecutionBackend = "auto",
        instrument: bool = False,
        timeout_seconds: int | None = None,
        memory_limit_mb: int | None = None,
    ) -> PlaygroundRunResponse:
        execution = ExecutionService.run_code(
            CodeExecutionRequest(
                code=code,
                stdin=input_text,
                backend=backend,
                instrument=instrument,
                timeout_seconds=timeout_seconds,
                memory_limit_mb=memory_limit_mb,
            )
        )
        return PlaygroundRunResponse(
            code=code,
            input=input_text,
            backend_requested=backend,
            instrumented=instrument,
            execution=execution,
        )

    @staticmethod
    def run_experiment(
        *,
        code: str,
        input_sizes: list[int],
        repetitions: int = 1,
        input_kind: InputKind = "array",
        input_profile: InputProfile = "random",
        backend: ExecutionBackend = "auto",
        instrument: bool = True,
        timeout_seconds: int | None = None,
        memory_limit_mb: int | None = None,
        entry_point: str | None = None,
    ) -> PlaygroundExperimentResponse:
        def factory() -> PlaygroundExperimentResponse:
            generator = InputGenerator()
            runs: list[PlaygroundExperimentRun] = []
            aggregated_runs: list[dict[str, Any]] = []

            for repetition_index in range(repetitions):
                for generated_input in generator.generate_series(
                    input_sizes,
                    kind=input_kind,
                    profile=input_profile,
                    seed=repetition_index,
                ):
                    execution = ExecutionService.run_code(
                        CodeExecutionRequest(
                            code=code,
                            stdin=generated_input.stdin,
                            backend=backend,
                            instrument=instrument,
                            timeout_seconds=timeout_seconds,
                            memory_limit_mb=memory_limit_mb,
                            entry_point=entry_point,
                        )
                    )
                    line_metrics = _build_line_metrics_from_instrumentation(execution, code=code)
                    function_metrics = _build_function_metrics_from_instrumentation(execution)
                    runs.append(
                        PlaygroundExperimentRun(
                            input_size=generated_input.input_size,
                            repetition_index=repetition_index,
                            input_kind=generated_input.kind,
                            input_profile=generated_input.profile,
                            generated_input={
                                "payload": generated_input.payload,
                                "stdin": generated_input.stdin,
                                "metadata": generated_input.metadata,
                            },
                            execution=execution,
                        )
                    )
                    aggregated_runs.append(
                        {
                            "input_size": generated_input.input_size,
                            "runtime_ms": execution.runtime_ms,
                            "line_metrics": [metric.model_dump() for metric in line_metrics],
                            "function_metrics": [metric.model_dump() for metric in function_metrics],
                        }
                    )

            snapshot = build_experiment_metrics_snapshot(aggregated_runs)
            complexity_estimate = None
            operations_complexity_estimate = None
            if aggregated_runs:
                analysis = ComplexityService.estimate_complexity(aggregated_runs, metric_name="runtime_ms")
                complexity_estimate = ComplexityEstimateRead.model_validate(
                    {
                        "id": "playground-runtime-estimate",
                        "experiment_id": None,
                        "metric_name": analysis.metric_name,
                        "estimated_class": analysis.estimated_class,
                        "confidence": analysis.confidence,
                        "sample_count": analysis.sample_count,
                        "explanation": analysis.explanation,
                        "alternatives": [asdict(alternative) for alternative in analysis.alternatives],
                        "evidence": analysis.evidence,
                        "created_at": analysis.created_at,
                        "updated_at": analysis.created_at,
                    }
                )

                # Build per-input-size operation totals by averaging across repetitions.
                # Total ops = sum of all line execution counts for that run.
                ops_by_size: dict[int, list[int]] = {}
                for agg in aggregated_runs:
                    size = agg["input_size"]
                    line_metrics_list = agg.get("line_metrics") or []
                    total_ops = sum(
                        m.get("execution_count", 0) if isinstance(m, dict) else getattr(m, "execution_count", 0)
                        for m in line_metrics_list
                    )
                    # Also add loop iteration counts which are a better signal
                    loop_total = sum(
                        m.get("loop_iterations", 0) if isinstance(m, dict) else getattr(m, "loop_iterations", 0)
                        for m in line_metrics_list
                    )
                    ops_by_size.setdefault(size, []).append(total_ops + loop_total)

                ops_samples = [
                    {"input_size": size, "total_operations": sum(counts) / len(counts)}
                    for size, counts in sorted(ops_by_size.items())
                    if counts and sum(counts) > 0
                ]

                if len(ops_samples) >= 3:
                    try:
                        ops_analysis = ComplexityService.estimate_complexity(
                            ops_samples,
                            metric_name="total_operations",
                            value_key="total_operations",
                        )
                        operations_complexity_estimate = ComplexityEstimateRead.model_validate(
                            {
                                "id": "playground-operations-estimate",
                                "experiment_id": None,
                                "metric_name": ops_analysis.metric_name,
                                "estimated_class": ops_analysis.estimated_class,
                                "confidence": ops_analysis.confidence,
                                "sample_count": ops_analysis.sample_count,
                                "explanation": ops_analysis.explanation,
                                "alternatives": [asdict(alternative) for alternative in ops_analysis.alternatives],
                                "evidence": ops_analysis.evidence,
                                "created_at": ops_analysis.created_at,
                                "updated_at": ops_analysis.created_at,
                            }
                        )
                    except (ValueError, ZeroDivisionError):
                        pass

            return PlaygroundExperimentResponse(
                code=code,
                backend_requested=backend,
                instrumented=instrument,
                input_kind=input_kind,
                input_profile=input_profile,
                repetitions=repetitions,
                runs=runs,
                metrics_snapshot=snapshot,
                complexity_estimate=complexity_estimate,
                operations_complexity_estimate=operations_complexity_estimate,
            )

        measured = measure(factory)
        return measured.value.model_copy(update={"orchestration_runtime_ms": measured.elapsed_ms})

    @staticmethod
    def get_status() -> PlaygroundStatusResponse:
        return PlaygroundStatusResponse(
            mode="stateless-playground",
            description=(
                "Open playground mode is active. Runs execute through the sandboxed execution "
                "service without requiring accounts or persistent project storage."
            ),
            backend_status=ExecutionService.get_backend_status(),
        )
