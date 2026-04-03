from __future__ import annotations

from fastapi import APIRouter
from pydantic import Field, field_validator

from app.experiments.input_generator import InputKind, InputProfile
from app.schemas.common import APIModel
from app.schemas.execution import ExecutionBackend
from app.services.playground_service import (
    PlaygroundExperimentResponse,
    PlaygroundRunResponse,
    PlaygroundService,
    PlaygroundStatusResponse,
)

router = APIRouter(prefix="/playground", tags=["playground"])


class PlaygroundRunRequest(APIModel):
    code: str = Field(min_length=1)
    input: str = ""
    backend: ExecutionBackend = "auto"
    instrument: bool = False
    timeout_seconds: int | None = Field(default=None, ge=1, le=30)
    memory_limit_mb: int | None = Field(default=None, ge=32, le=1024)


class PlaygroundExperimentRequest(APIModel):
    code: str = Field(min_length=1)
    input_sizes: list[int] = Field(default_factory=list)
    input_kind: InputKind = "array"
    input_profile: InputProfile = "random"
    repetitions: int = Field(default=1, ge=1, le=100)
    backend: ExecutionBackend = "auto"
    instrument: bool = True
    timeout_seconds: int | None = Field(default=None, ge=1, le=30)
    memory_limit_mb: int | None = Field(default=None, ge=32, le=1024)
    entry_point: str | None = Field(default=None, description="Name of the function to call as the experiment entry point. Auto-detected if not provided.")

    @field_validator("input_sizes")
    @classmethod
    def validate_input_sizes(cls, value: list[int]) -> list[int]:
        if any(size <= 0 for size in value):
            raise ValueError("All input sizes must be positive integers")
        if value and max(value) < 10:
            raise ValueError("Input sizes should be at least 10 for meaningful complexity analysis")
        return value


@router.get("/status", response_model=PlaygroundStatusResponse)
def get_playground_status() -> PlaygroundStatusResponse:
    return PlaygroundService.get_status()


@router.post("/run", response_model=PlaygroundRunResponse)
def run_playground_code(payload: PlaygroundRunRequest) -> PlaygroundRunResponse:
    return PlaygroundService.run_code(
        code=payload.code,
        input_text=payload.input,
        backend=payload.backend,
        instrument=payload.instrument,
        timeout_seconds=payload.timeout_seconds,
        memory_limit_mb=payload.memory_limit_mb,
    )


@router.post("/experiment", response_model=PlaygroundExperimentResponse)
def run_playground_experiment(payload: PlaygroundExperimentRequest) -> PlaygroundExperimentResponse:
    return PlaygroundService.run_experiment(
        code=payload.code,
        input_sizes=payload.input_sizes,
        repetitions=payload.repetitions,
        input_kind=payload.input_kind,
        input_profile=payload.input_profile,
        backend=payload.backend,
        instrument=payload.instrument,
        timeout_seconds=payload.timeout_seconds,
        memory_limit_mb=payload.memory_limit_mb,
        entry_point=payload.entry_point,
    )
