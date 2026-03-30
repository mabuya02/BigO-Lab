from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from sqlalchemy.orm import Session

from app.experiments.aggregator import build_experiment_metrics_snapshot
from app.experiments.input_generator import GeneratedInput, InputGenerator, InputKind, InputProfile
from app.services.execution_service import ExecutionService
from app.services.metrics_service import MetricsService
from app.schemas.execution import CodeExecutionRequest, CodeExecutionResult


@dataclass(slots=True)
class ExperimentRunOutcome:
    input_size: int
    repetition_index: int
    generated_input: GeneratedInput
    execution_result: CodeExecutionResult
    persisted_run_id: str | None = None


@dataclass(slots=True)
class ExperimentSeriesResult:
    experiment_id: str
    outcomes: list[ExperimentRunOutcome] = field(default_factory=list)
    snapshot: object | None = None


class ExperimentOrchestrator:
    def __init__(self, input_generator: InputGenerator | None = None) -> None:
        self.input_generator = input_generator or InputGenerator()

    def run_series(
        self,
        *,
        experiment_id: str,
        code: str,
        input_sizes: Sequence[int],
        repetitions: int = 1,
        kind: InputKind = "array",
        profile: InputProfile = "random",
        backend: str = "auto",
        language: str = "python",
        db: Session | None = None,
    ) -> ExperimentSeriesResult:
        outcomes: list[ExperimentRunOutcome] = []
        for repetition_index in range(repetitions):
            generated_inputs = self.input_generator.generate_series(
                input_sizes,
                kind=kind,
                profile=profile,
                seed=repetition_index,
            )
            for generated_input in generated_inputs:
                execution_request = CodeExecutionRequest(
                    code=code,
                    stdin=generated_input.stdin,
                    backend=backend,
                    language=language,
                    instrument=True,
                )
                execution_result = ExecutionService.run_code(execution_request)
                persisted_run_id = None
                if db is not None:
                    persisted_run = MetricsService.save_execution_result(
                        db,
                        experiment_id=experiment_id,
                        input_size=generated_input.input_size,
                        repetition_index=repetition_index,
                        input_profile=generated_input.profile,
                        input_payload=generated_input.payload,
                        execution_result=execution_result,
                    )
                    persisted_run_id = persisted_run.id
                outcomes.append(
                    ExperimentRunOutcome(
                        input_size=generated_input.input_size,
                        repetition_index=repetition_index,
                        generated_input=generated_input,
                        execution_result=execution_result,
                        persisted_run_id=persisted_run_id,
                    )
                )
        snapshot = build_experiment_metrics_snapshot(
            [
                {
                    "input_size": outcome.input_size,
                    "runtime_ms": outcome.execution_result.runtime_ms,
                    "line_metrics": outcome.execution_result.instrumentation.line_counts
                    if outcome.execution_result.instrumentation
                    else [],
                    "function_metrics": outcome.execution_result.instrumentation.function_call_counts
                    if outcome.execution_result.instrumentation
                    else [],
                }
                for outcome in outcomes
            ]
        )
        if db is not None:
            snapshot = MetricsService.get_experiment_metrics(db, experiment_id)
        return ExperimentSeriesResult(
            experiment_id=experiment_id,
            outcomes=outcomes,
            snapshot=snapshot,
        )


def run_experiment_series(
    *,
    experiment_id: str,
    code: str,
    input_sizes: Sequence[int],
    repetitions: int = 1,
    kind: InputKind = "array",
    profile: InputProfile = "random",
    backend: str = "auto",
    language: str = "python",
    db: Session | None = None,
) -> ExperimentSeriesResult:
    orchestrator = ExperimentOrchestrator()
    return orchestrator.run_series(
        experiment_id=experiment_id,
        code=code,
        input_sizes=input_sizes,
        repetitions=repetitions,
        kind=kind,
        profile=profile,
        backend=backend,
        language=language,
        db=db,
    )
