from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.code_snippet import CodeSnippetCreate, CodeSnippetRead, CodeSnippetUpdate
from app.services.snippet_service import SnippetService

router = APIRouter(prefix="/projects/{project_id}/snippets", tags=["snippets"])


@router.get("", response_model=list[CodeSnippetRead])
def list_project_snippets(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CodeSnippetRead]:
    snippets = SnippetService.list_for_project(db, project_id, current_user)
    return [CodeSnippetRead.model_validate(snippet) for snippet in snippets]


@router.post("", response_model=CodeSnippetRead, status_code=status.HTTP_201_CREATED)
def create_project_snippet(
    project_id: str,
    payload: CodeSnippetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CodeSnippetRead:
    snippet = SnippetService.create_snippet(db, project_id, current_user, payload)
    return CodeSnippetRead.model_validate(snippet)


@router.get("/{snippet_id}", response_model=CodeSnippetRead)
def get_project_snippet(
    project_id: str,
    snippet_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CodeSnippetRead:
    snippet = SnippetService.get_for_project(db, project_id, snippet_id, current_user)
    return CodeSnippetRead.model_validate(snippet)


@router.put("/{snippet_id}", response_model=CodeSnippetRead)
def update_project_snippet(
    project_id: str,
    snippet_id: str,
    payload: CodeSnippetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CodeSnippetRead:
    snippet = SnippetService.update_snippet(db, project_id, snippet_id, current_user, payload)
    return CodeSnippetRead.model_validate(snippet)
