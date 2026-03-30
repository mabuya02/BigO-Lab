from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.experiments.orchestrator import ExperimentOrchestrator
from app.models import CodeSnippet, ComplexityEstimate, Experiment, User
from app.schemas.complexity import ComplexityEstimateRead
from app.schemas.experiment import ExperimentCreate, ExperimentDetail, ExperimentExecuteRequest, ExperimentRead
from app.services.project_service import ProjectService
from app.services.complexity_service import ComplexityService
from app.services.metrics_service import MetricsService


class ExperimentService:
    @staticmethod
    def list_for_project(db: Session, project_id: str, user: User) -> list[Experiment]:
        project = ProjectService.get_for_user(db, project_id, user)
        return (
            db.query(Experiment)
            .filter(Experiment.project_id == project.id)
            .order_by(Experiment.updated_at.desc())
            .all()
        )

    @staticmethod
    def create_experiment(
        db: Session,
        project_id: str,
        user: User,
        payload: ExperimentCreate,
    ) -> Experiment:
        project = ProjectService.get_for_user(db, project_id, user)

        if payload.snippet_id:
            snippet = (
                db.query(CodeSnippet)
                .filter(
                    CodeSnippet.id == payload.snippet_id,
                    CodeSnippet.project_id == project.id,
                )
                .first()
            )
            if snippet is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Snippet not found for this project",
                )

        experiment = Experiment(
            project_id=project.id,
            snippet_id=payload.snippet_id,
            created_by_id=user.id,
            name=payload.name,
            language=payload.language,
            input_kind=payload.input_kind,
            input_profile=payload.input_profile,
            input_sizes=payload.input_sizes,
            repetitions=payload.repetitions,
        )
        db.add(experiment)
        db.commit()
        db.refresh(experiment)
        return experiment

    @staticmethod
    def get_for_project(db: Session, project_id: str, experiment_id: str, user: User) -> Experiment:
        project = ProjectService.get_for_user(db, project_id, user)
        experiment = (
            db.query(Experiment)
            .filter(Experiment.id == experiment_id, Experiment.project_id == project.id)
            .first()
        )
        if experiment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
        return experiment

    @classmethod
    def get_experiment_detail(
        cls,
        db: Session,
        project_id: str,
        experiment_id: str,
        user: User,
    ) -> ExperimentDetail:
        experiment = cls.get_for_project(db, project_id, experiment_id, user)
        runs = MetricsService.list_runs_as_schema(db, experiment.id)
        metrics_snapshot = MetricsService.get_experiment_metrics(db, experiment.id) if runs else None
        latest_complexity_estimate = (
            ComplexityEstimateRead.model_validate(experiment.complexity_estimates[0])
            if getattr(experiment, "complexity_estimates", None)
            else None
        )
        base_payload = ExperimentRead.model_validate(experiment).model_dump()
        return ExperimentDetail(
            **base_payload,
            runs=runs,
            metrics_snapshot=metrics_snapshot,
            latest_complexity_estimate=latest_complexity_estimate,
        )

    @classmethod
    def run_experiment(
        cls,
        db: Session,
        project_id: str,
        experiment_id: str,
        user: User,
        payload: ExperimentExecuteRequest,
    ) -> ExperimentDetail:
        experiment = cls.get_for_project(db, project_id, experiment_id, user)
        if experiment.snippet is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Experiment is not linked to a code snippet",
            )

        experiment.status = "running"
        db.add(experiment)
        db.commit()
        db.refresh(experiment)

        orchestrator = ExperimentOrchestrator()
        orchestrator.run_series(
            experiment_id=experiment.id,
            code=experiment.snippet.code,
            input_sizes=experiment.input_sizes,
            repetitions=experiment.repetitions,
            kind=experiment.input_kind,  # type: ignore[arg-type]
            profile=(experiment.input_profile or "random"),  # type: ignore[arg-type]
            backend=payload.backend,
            language=experiment.language,
            db=db,
        )

        experiment.status = "completed"
        db.add(experiment)

        runs = MetricsService.list_runs(db, experiment.id)
        if payload.refresh_complexity and runs:
            analysis = ComplexityService.estimate_complexity(runs, metric_name="runtime_ms")
            complexity_estimate = ComplexityEstimate(**ComplexityService.to_model(analysis, experiment_id=experiment.id))
            db.add(complexity_estimate)

        db.commit()
        db.refresh(experiment)
        return cls.get_experiment_detail(db, project_id, experiment_id, user)
