from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.project import ProjectCreate, ProjectRead
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectRead])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ProjectRead]:
    projects = ProjectService.list_for_user(db, current_user)
    return [ProjectRead.model_validate(project) for project in projects]


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectRead:
    project = ProjectService.create_project(db, current_user, payload)
    return ProjectRead.model_validate(project)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectRead:
    project = ProjectService.get_for_user(db, project_id, current_user)
    return ProjectRead.model_validate(project)
