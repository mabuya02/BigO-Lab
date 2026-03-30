from __future__ import annotations

from fastapi import HTTPException, status

from app.presets.library import PRESET_ALGORITHMS, get_preset_definition, list_preset_categories
from app.schemas.preset import PresetCatalogRead, PresetCategoryRead, PresetRead


class PresetService:
    @staticmethod
    def list_categories() -> list[PresetCategoryRead]:
        return [PresetCategoryRead.model_validate(category) for category in list_preset_categories()]

    @classmethod
    def list_presets(cls, category: str | None = None) -> PresetCatalogRead:
        presets = [
            PresetRead.model_validate(preset.to_dict())
            for preset in PRESET_ALGORITHMS
            if category is None or preset.category == category
        ]
        categories = cls.list_categories()
        if category is not None and not any(item.slug == category for item in categories):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preset category not found")
        if category is not None:
            categories = [item for item in categories if item.slug == category]
        return PresetCatalogRead(categories=categories, presets=presets)

    @staticmethod
    def get_preset(slug: str) -> PresetRead:
        preset = get_preset_definition(slug)
        if preset is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preset not found")
        return PresetRead.model_validate(preset.to_dict())
