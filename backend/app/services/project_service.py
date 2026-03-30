from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Project, User
from app.schemas.project import ProjectCreate


class ProjectService:
    @staticmethod
    def list_for_user(db: Session, user: User) -> list[Project]:
        return (
            db.query(Project)
            .filter(Project.owner_id == user.id)
            .order_by(Project.updated_at.desc())
            .all()
        )

    @staticmethod
    def get_for_user(db: Session, project_id: str, user: User) -> Project:
        project = (
            db.query(Project)
            .filter(Project.id == project_id, Project.owner_id == user.id)
            .first()
        )
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return project

    @staticmethod
    def create_project(db: Session, user: User, payload: ProjectCreate) -> Project:
        project = Project(
            owner_id=user.id,
            name=payload.name,
            description=payload.description,
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return project
