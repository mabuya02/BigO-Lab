from __future__ import annotations

try:
    import dramatiq
except Exception:  # pragma: no cover - optional dependency path
    dramatiq = None

from app.services.execution_service import ExecutionService


def _run_execution_job(job_id: str, payload: dict, user_id: str) -> None:
    ExecutionService.process_job(job_id, payload, user_id)


if dramatiq is not None:

    @dramatiq.actor(queue_name="execution", max_retries=0)
    def execute_code_job(job_id: str, payload: dict, user_id: str) -> None:
        _run_execution_job(job_id, payload, user_id)

else:

    def execute_code_job(job_id: str, payload: dict, user_id: str) -> None:
        _run_execution_job(job_id, payload, user_id)
