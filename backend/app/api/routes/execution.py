from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from app.schemas.execution import (
    CodeExecutionJob,
    CodeExecutionRequest,
    CodeExecutionResult,
    ExecutionBackendStatus,
)
from app.services.execution_service import ExecutionService

router = APIRouter(prefix="/execution", tags=["execution"])


@router.get("/status", response_model=ExecutionBackendStatus, status_code=status.HTTP_200_OK)
def execution_status() -> ExecutionBackendStatus:
    return ExecutionService.get_backend_status()


@router.post("/run", response_model=CodeExecutionResult)
def run_code(payload: CodeExecutionRequest) -> CodeExecutionResult:
    try:
        return ExecutionService.run_code(payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.post("/jobs", response_model=CodeExecutionJob, status_code=status.HTTP_202_ACCEPTED)
def queue_code_execution(payload: CodeExecutionRequest) -> CodeExecutionJob:
    try:
        return ExecutionService.submit_job(payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.get("/jobs/{job_id}", response_model=CodeExecutionJob)
def get_execution_job(job_id: str) -> CodeExecutionJob:
    return ExecutionService.get_job(job_id)
