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
from app.schemas.metrics import ExperimentMetricsSnapshot
from app.services.execution_service import ExecutionService
from app.services.metrics_service import MetricsService


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
                        )
                    )
                    line_metrics = MetricsService.build_line_metrics_from_instrumentation(execution)
                    function_metrics = MetricsService.build_function_metrics_from_instrumentation(execution)
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
