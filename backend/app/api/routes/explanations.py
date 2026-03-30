from __future__ import annotations

from fastapi import APIRouter

from app.schemas.explanation import ExplanationRequest, ExplanationResponse
from app.services.explanation_service import ExplanationService

router = APIRouter(prefix="/explanations", tags=["explanations"])


@router.post("/generate", response_model=ExplanationResponse)
def generate_explanation(payload: ExplanationRequest) -> ExplanationResponse:
    return ExplanationService.generate(payload)


__all__ = ["router"]
