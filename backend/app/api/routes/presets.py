from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.schemas.preset import PresetCatalogRead, PresetRead
from app.services.preset_service import PresetService

router = APIRouter(prefix="/presets", tags=["presets"])


@router.get("", response_model=PresetCatalogRead, status_code=status.HTTP_200_OK)
def list_presets(category: str | None = Query(default=None)) -> PresetCatalogRead:
    return PresetService.list_presets(category=category)


@router.get("/{slug}", response_model=PresetRead, status_code=status.HTTP_200_OK)
def get_preset(slug: str) -> PresetRead:
    return PresetService.get_preset(slug)
