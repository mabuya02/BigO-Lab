from __future__ import annotations

from pydantic import Field

from app.schemas.common import APIModel


class PresetCategoryRead(APIModel):
    slug: str
    name: str
    description: str
    preset_count: int


class PresetRead(APIModel):
    slug: str
    name: str
    category: str
    summary: str
    description: str
    language: str
    input_kind: str
    input_profile: str
    expected_complexity: str
    starter_code: str
    tags: list[str] = Field(default_factory=list)
    default_input_sizes: list[int] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class PresetCatalogRead(APIModel):
    categories: list[PresetCategoryRead] = Field(default_factory=list)
    presets: list[PresetRead] = Field(default_factory=list)
