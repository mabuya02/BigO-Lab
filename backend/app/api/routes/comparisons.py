from __future__ import annotations

from fastapi import APIRouter

from app.schemas.comparison import ComparisonReport, ComparisonRequest
from app.services.comparison_service import ComparisonService

router = APIRouter(prefix="/comparisons", tags=["comparisons"])


@router.post("/compare", response_model=ComparisonReport)
def compare(payload: ComparisonRequest) -> ComparisonReport:
    return ComparisonService.compare(payload)
