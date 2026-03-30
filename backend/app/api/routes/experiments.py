from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.experiment import ExperimentCreate, ExperimentDetail, ExperimentExecuteRequest, ExperimentRead
from app.schemas.experiment_run import ExperimentRunRead
from app.schemas.metrics import ExperimentMetricsSnapshot
from app.services.experiment_service import ExperimentService
from app.services.metrics_service import MetricsService

router = APIRouter(prefix="/projects/{project_id}/experiments", tags=["experiments"])


@router.get("", response_model=list[ExperimentRead])
def list_project_experiments(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ExperimentRead]:
    experiments = ExperimentService.list_for_project(db, project_id, current_user)
    return [ExperimentRead.model_validate(experiment) for experiment in experiments]


@router.post("", response_model=ExperimentRead, status_code=status.HTTP_201_CREATED)
def create_project_experiment(
    project_id: str,
    payload: ExperimentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExperimentRead:
    experiment = ExperimentService.create_experiment(db, project_id, current_user, payload)
    return ExperimentRead.model_validate(experiment)


@router.get("/{experiment_id}", response_model=ExperimentDetail)
def get_project_experiment(
    project_id: str,
    experiment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExperimentDetail:
    return ExperimentService.get_experiment_detail(db, project_id, experiment_id, current_user)


@router.post("/{experiment_id}/run", response_model=ExperimentDetail)
def run_project_experiment(
    project_id: str,
    experiment_id: str,
    payload: ExperimentExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExperimentDetail:
    return ExperimentService.run_experiment(db, project_id, experiment_id, current_user, payload)


@router.get("/{experiment_id}/runs", response_model=list[ExperimentRunRead])
def list_project_experiment_runs(
    project_id: str,
    experiment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ExperimentRunRead]:
    experiment = ExperimentService.get_for_project(db, project_id, experiment_id, current_user)
    return MetricsService.list_runs_as_schema(db, experiment.id)


@router.get("/{experiment_id}/metrics", response_model=ExperimentMetricsSnapshot)
def get_project_experiment_metrics(
    project_id: str,
    experiment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExperimentMetricsSnapshot:
    experiment = ExperimentService.get_for_project(db, project_id, experiment_id, current_user)
    return MetricsService.get_experiment_metrics(db, experiment.id)
