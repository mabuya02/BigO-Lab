from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import CodeSnippet, User
from app.schemas.code_snippet import CodeSnippetCreate, CodeSnippetUpdate
from app.services.project_service import ProjectService


class SnippetService:
    @staticmethod
    def list_for_project(db: Session, project_id: str, user: User) -> list[CodeSnippet]:
        project = ProjectService.get_for_user(db, project_id, user)
        return (
            db.query(CodeSnippet)
            .filter(CodeSnippet.project_id == project.id)
            .order_by(CodeSnippet.updated_at.desc())
            .all()
        )

    @staticmethod
    def get_for_project(db: Session, project_id: str, snippet_id: str, user: User) -> CodeSnippet:
        project = ProjectService.get_for_user(db, project_id, user)
        snippet = (
            db.query(CodeSnippet)
            .filter(
                CodeSnippet.id == snippet_id,
                CodeSnippet.project_id == project.id,
            )
            .first()
        )
        if snippet is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snippet not found")
        return snippet

    @staticmethod
    def create_snippet(
        db: Session,
        project_id: str,
        user: User,
        payload: CodeSnippetCreate,
    ) -> CodeSnippet:
        project = ProjectService.get_for_user(db, project_id, user)
        snippet = CodeSnippet(
            project_id=project.id,
            author_id=user.id,
            title=payload.title,
            language=payload.language,
            code=payload.code,
        )
        db.add(snippet)
        db.commit()
        db.refresh(snippet)
        return snippet

    @staticmethod
    def update_snippet(
        db: Session,
        project_id: str,
        snippet_id: str,
        user: User,
        payload: CodeSnippetUpdate,
    ) -> CodeSnippet:
        snippet = SnippetService.get_for_project(db, project_id, snippet_id, user)
        updates = payload.model_dump(exclude_unset=True, exclude_none=True)
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provide at least one field to update",
            )

        code_updated = "code" in updates and updates["code"] != snippet.code

        for field_name, value in updates.items():
            setattr(snippet, field_name, value)

        if code_updated:
            snippet.version += 1

        db.add(snippet)
        db.commit()
        db.refresh(snippet)
        return snippet
