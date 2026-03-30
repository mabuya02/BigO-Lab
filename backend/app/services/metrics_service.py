from __future__ import annotations

from typing import Sequence

from sqlalchemy.orm import Session, selectinload

from app.experiments.aggregator import (
    aggregate_function_metrics,
    aggregate_line_metrics,
    aggregate_runs,
    build_experiment_metrics_snapshot,
)
from app.models import ExperimentRun, FunctionMetric, LineMetric
from app.schemas.execution import CodeExecutionResult
from app.schemas.experiment_run import ExperimentRunCreate, ExperimentRunRead, ExperimentRunUpdate
from app.schemas.metrics import (
    AggregatedFunctionMetric,
    AggregatedLineMetric,
    ExperimentMetricsSnapshot,
    FunctionMetricCreate,
    LineMetricCreate,
)
from app.utils.helpers import utcnow

class MetricsService:
    @staticmethod
    def create_experiment_run(db: Session, payload: ExperimentRunCreate) -> ExperimentRun:
        run = ExperimentRun(
            experiment_id=payload.experiment_id,
            input_size=payload.input_size,
            repetition_index=payload.repetition_index,
            input_profile=payload.input_profile,
            input_payload=payload.input_payload,
            status=payload.status,
            backend=payload.backend,
        )
        db.add(run)
        db.flush()
        return run

    @staticmethod
    def update_experiment_run(
        db: Session,
        run: ExperimentRun,
        payload: ExperimentRunUpdate,
    ) -> ExperimentRun:
        updates = payload.model_dump(exclude_unset=True, exclude_none=True)
        for field_name, value in updates.items():
            setattr(run, field_name, value)
        db.add(run)
        db.flush()
        return run

    @staticmethod
    def _persist_line_metrics(
        db: Session,
        run: ExperimentRun,
        metrics: Sequence[LineMetricCreate | dict],
    ) -> list[LineMetric]:
        persisted: list[LineMetric] = []
        for metric in metrics:
            metric_data = metric.model_dump() if hasattr(metric, "model_dump") else dict(metric)
            row = LineMetric(
                experiment_run_id=run.id,
                **metric_data,
            )
            db.add(row)
            persisted.append(row)
        return persisted

    @staticmethod
    def _persist_function_metrics(
        db: Session,
        run: ExperimentRun,
        metrics: Sequence[FunctionMetricCreate | dict],
    ) -> list[FunctionMetric]:
        persisted: list[FunctionMetric] = []
        for metric in metrics:
            metric_data = metric.model_dump() if hasattr(metric, "model_dump") else dict(metric)
            row = FunctionMetric(
                experiment_run_id=run.id,
                **metric_data,
            )
            db.add(row)
            persisted.append(row)
        return persisted

    @classmethod
    def save_execution_result(
        cls,
        db: Session,
        *,
        experiment_id: str,
        input_size: int,
        repetition_index: int,
        input_profile: str | None,
        input_payload: object | None,
        execution_result: CodeExecutionResult,
        line_metrics: Sequence[LineMetricCreate | dict] | None = None,
        function_metrics: Sequence[FunctionMetricCreate | dict] | None = None,
    ) -> ExperimentRun:
        if execution_result.instrumentation is not None:
            if line_metrics is None:
                line_metrics = cls.build_line_metrics_from_instrumentation(execution_result)
            if function_metrics is None:
                function_metrics = cls.build_function_metrics_from_instrumentation(execution_result)

        run = cls.create_experiment_run(
            db,
            ExperimentRunCreate(
                experiment_id=experiment_id,
                input_size=input_size,
                repetition_index=repetition_index,
                input_profile=input_profile,
                input_payload=input_payload,
                status=execution_result.status,
                backend=execution_result.backend,
            ),
        )
        run.status = execution_result.status
        run.backend = execution_result.backend
        run.runtime_ms = execution_result.runtime_ms
        run.stdout = execution_result.stdout
        run.stderr = execution_result.stderr
        run.exit_code = execution_result.exit_code
        run.timed_out = execution_result.timed_out
        run.truncated_stdout = execution_result.truncated_stdout
        run.truncated_stderr = execution_result.truncated_stderr
        run.finished_at = utcnow()
        if line_metrics:
            cls._persist_line_metrics(db, run, line_metrics)
        if function_metrics:
            cls._persist_function_metrics(db, run, function_metrics)
        db.commit()
        db.refresh(run)
        return run

    @staticmethod
    def build_line_metrics_from_instrumentation(
        execution_result: CodeExecutionResult,
    ) -> list[LineMetricCreate]:
        instrumentation = execution_result.instrumentation
        if instrumentation is None:
            return []

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
                    nesting_depth=0,
                    loop_iterations=loop_iterations_by_line.get(line_number, 0),
                    branch_visits=0,
                )
            )
        return metrics

    @staticmethod
    def build_function_metrics_from_instrumentation(
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

    @staticmethod
    def list_runs(db: Session, experiment_id: str) -> list[ExperimentRun]:
        return (
            db.query(ExperimentRun)
            .filter(ExperimentRun.experiment_id == experiment_id)
            .options(
                selectinload(ExperimentRun.line_metrics),
                selectinload(ExperimentRun.function_metrics),
            )
            .order_by(ExperimentRun.input_size.asc(), ExperimentRun.repetition_index.asc())
            .all()
        )

    @classmethod
    def get_experiment_metrics(cls, db: Session, experiment_id: str) -> ExperimentMetricsSnapshot:
        runs = cls.list_runs(db, experiment_id)
        return build_experiment_metrics_snapshot(runs)

    @classmethod
    def list_runs_as_schema(cls, db: Session, experiment_id: str) -> list[ExperimentRunRead]:
        runs = cls.list_runs(db, experiment_id)
        snapshot = cls.get_experiment_metrics(db, experiment_id)
        return [
            ExperimentRunRead.model_validate(run).model_copy(update={"summary": snapshot.summary})
            for run in runs
        ]

    @staticmethod
    def summarize_line_metrics(metrics: Sequence[LineMetric]) -> list[AggregatedLineMetric]:
        return aggregate_line_metrics(metrics)

    @staticmethod
    def summarize_function_metrics(metrics: Sequence[FunctionMetric]) -> list[AggregatedFunctionMetric]:
        return aggregate_function_metrics(metrics)

    @staticmethod
    def summarize_runs(runs: Sequence[ExperimentRun]):
        return aggregate_runs(runs)
