from __future__ import annotations

import ast
import json
from threading import Lock, Thread
from uuid import uuid4

from fastapi import HTTPException, status

from app.core.settings import get_settings
from app.execution.runner import DockerPythonRunner, LocalPythonRunner, docker_cli_available
from app.execution.sandbox import SandboxExecutionResult, SandboxLimits
from app.instrumentation.parser import instrument_source
from app.schemas.execution import (
    CodeExecutionJob,
    CodeExecutionRequest,
    CodeExecutionResult,
    ExecutionInstrumentationReport,
    ExecutionBackendStatus,
)
from app.utils.helpers import utcnow
from app.workers.broker import broker_available, enqueue_execution_job

INSTRUMENTATION_MARKER = "__BIG_O_METRICS__:"
TRACKER_RUNTIME_SOURCE = f"""
from collections import Counter as _big_o_counter
import json as _big_o_json
import sys as _big_o_sys

class _BigOTracker:
    def __init__(self):
        self.line_counts = _big_o_counter()
        self.function_call_counts = _big_o_counter()
        self.loop_iteration_counts = _big_o_counter()

    def line(self, line_no):
        self.line_counts[int(line_no)] += 1

    def function_call(self, qualname):
        self.function_call_counts[str(qualname)] += 1

    def loop_iteration(self, loop_key):
        self.loop_iteration_counts[str(loop_key)] += 1

    def snapshot(self):
        return {{
            "line_counts": dict(self.line_counts),
            "function_call_counts": dict(self.function_call_counts),
            "loop_iteration_counts": dict(self.loop_iteration_counts),
        }}

_big_o_tracker = _BigOTracker()

def __big_o_emit_metrics():
    _big_o_sys.stderr.write("{INSTRUMENTATION_MARKER}" + _big_o_json.dumps(_big_o_tracker.snapshot(), separators=(",", ":")) + "\\n")
"""


class ExecutionService:
    _jobs: dict[str, dict[str, object]] = {}
    _job_lock = Lock()

    @classmethod
    def get_backend_status(cls) -> ExecutionBackendStatus:
        settings = get_settings()
        docker_runner = DockerPythonRunner(
            image=settings.execution_docker_image,
            workspace_root=settings.execution_workspace_root,
        )
        return ExecutionBackendStatus(
            execution_backend=settings.execution_backend,
            queue_backend=settings.execution_queue_backend,
            local_fallback_enabled=settings.execution_allow_local_fallback,
            docker_cli_available=docker_cli_available(),
            docker_image_available=docker_runner.image_available(),
            dramatiq_available=broker_available(),
            redis_configured=bool(settings.redis_url),
            sandbox_image=settings.execution_docker_image,
            default_timeout_seconds=settings.execution_default_timeout_seconds,
            max_timeout_seconds=settings.execution_max_timeout_seconds,
            memory_limit_mb=settings.execution_memory_limit_mb,
        )

    @classmethod
    def run_code(cls, payload: CodeExecutionRequest) -> CodeExecutionResult:
        runner = cls._select_runner(payload.backend)
        limits = cls._build_limits(payload)
        code_to_run = payload.code
        instrumentation_metadata = None
        if payload.instrument:
            try:
                instrumented = instrument_source(payload.code)
                code_to_run = cls._build_instrumented_runtime_source(
                    instrumented.instrumented_source,
                    forced_entry_point=payload.entry_point,
                )
                instrumentation_metadata = instrumented.metadata
            except SyntaxError as exc:
                return CodeExecutionResult(
                    status="failed",
                    stdout="",
                    stderr=str(exc),
                    exit_code=1,
                    runtime_ms=0,
                    backend="instrumentation",
                )

        result = runner.run(code_to_run, payload.stdin, limits)
        return cls._to_schema_result(result, instrumentation_metadata=instrumentation_metadata)

    @classmethod
    def submit_job(cls, payload: CodeExecutionRequest, owner_id: str | None = None) -> CodeExecutionJob:
        settings = get_settings()
        job_id = str(uuid4())
        queue_backend = settings.execution_queue_backend
        job = CodeExecutionJob(
            job_id=job_id,
            status="queued",
            queue_backend=queue_backend if queue_backend != "auto" else "local-thread",
            backend_requested=payload.backend,
            submitted_at=utcnow(),
        )
        with cls._job_lock:
            cls._jobs[job_id] = {"owner_id": owner_id, "job": job}

        payload_dict = payload.model_dump()
        worker_owner_id = owner_id or "anonymous"
        if queue_backend in {"auto", "dramatiq"} and enqueue_execution_job(job_id, payload_dict, worker_owner_id):
            cls._update_job(job_id, queue_backend="dramatiq")
            return cls.get_job(job_id, owner_id)

        if queue_backend == "dramatiq":
            raise RuntimeError("Dramatiq queue requested but is not available")

        worker = Thread(
            target=cls.process_job,
            args=(job_id, payload_dict, worker_owner_id),
            daemon=True,
            name=f"execution-job-{job_id}",
        )
        worker.start()
        return cls.get_job(job_id, owner_id)

    @classmethod
    def get_job(cls, job_id: str, owner_id: str | None = None) -> CodeExecutionJob:
        with cls._job_lock:
            record = cls._jobs.get(job_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution job not found")
        record_owner_id = record["owner_id"]
        if record_owner_id is not None and record_owner_id != owner_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution job not found")
        return record["job"]  # type: ignore[return-value]

    @classmethod
    def process_job(cls, job_id: str, payload_dict: dict, user_id: str) -> None:
        payload = CodeExecutionRequest.model_validate(payload_dict)
        cls._update_job(job_id, status="running", started_at=utcnow())
        try:
            result = cls.run_code(payload)
            final_status = "completed" if result.status == "completed" else result.status
            cls._update_job(
                job_id,
                status=final_status,
                backend_used=result.backend,
                result=result,
                finished_at=utcnow(),
            )
        except Exception as exc:
            cls._update_job(
                job_id,
                status="failed",
                error=str(exc),
                finished_at=utcnow(),
            )

    @classmethod
    def _build_limits(cls, payload: CodeExecutionRequest) -> SandboxLimits:
        settings = get_settings()
        timeout_seconds = payload.timeout_seconds or settings.execution_default_timeout_seconds
        timeout_seconds = min(timeout_seconds, settings.execution_max_timeout_seconds)
        memory_limit_mb = payload.memory_limit_mb or settings.execution_memory_limit_mb
        return SandboxLimits(
            timeout_seconds=timeout_seconds,
            memory_limit_mb=memory_limit_mb,
            cpu_limit=settings.execution_cpu_limit,
            output_limit_bytes=settings.execution_output_limit_bytes,
        )

    @classmethod
    def _select_runner(cls, requested_backend: str):
        settings = get_settings()
        docker_runner = DockerPythonRunner(
            image=settings.execution_docker_image,
            workspace_root=settings.execution_workspace_root,
        )
        local_runner = LocalPythonRunner(workspace_root=settings.execution_workspace_root)

        backend = requested_backend if requested_backend != "auto" else settings.execution_backend

        if backend == "docker":
            if docker_runner.is_available():
                return docker_runner
            raise RuntimeError("Docker execution is configured but the sandbox image is unavailable")

        if backend == "local":
            if settings.execution_allow_local_fallback:
                return local_runner
            raise RuntimeError("Local execution fallback is disabled")

        if docker_runner.is_available():
            return docker_runner
        if settings.execution_allow_local_fallback:
            return local_runner
        raise RuntimeError("No execution backend is available")

    @classmethod
    def _to_schema_result(
        cls,
        result: SandboxExecutionResult,
        *,
        instrumentation_metadata=None,
    ) -> CodeExecutionResult:
        stderr = result.stderr
        instrumentation_report = None
        if instrumentation_metadata is not None:
            stderr, instrumentation_report = cls._extract_instrumentation(stderr, instrumentation_metadata)

        return CodeExecutionResult(
            status=result.status,  # type: ignore[arg-type]
            stdout=result.stdout,
            stderr=stderr,
            exit_code=result.exit_code,
            runtime_ms=result.runtime_ms,
            backend=result.backend,
            timed_out=result.timed_out,
            truncated_stdout=result.truncated_stdout,
            truncated_stderr=result.truncated_stderr,
            instrumentation=instrumentation_report,
        )

    @classmethod
    def _update_job(cls, job_id: str, **updates) -> None:
        with cls._job_lock:
            record = cls._jobs.get(job_id)
            if record is None:
                return
            job: CodeExecutionJob = record["job"]  # type: ignore[assignment]
            record["job"] = job.model_copy(update=updates)

    @staticmethod
    def _split_module_prologue(body: list[ast.stmt]) -> tuple[list[ast.stmt], list[ast.stmt]]:
        index = 0
        if (
            index < len(body)
            and isinstance(body[index], ast.Expr)
            and isinstance(body[index].value, ast.Constant)
            and isinstance(body[index].value.value, str)
        ):
            index += 1
        while index < len(body) and isinstance(body[index], ast.ImportFrom) and body[index].module == "__future__":
            index += 1
        return body[:index], body[index:]

    @classmethod
    def _build_instrumented_runtime_source(
        cls, instrumented_source: str, *, forced_entry_point: str | None = None
    ) -> str:
        tree = ast.parse(instrumented_source, mode="exec")
        prologue, body = cls._split_module_prologue(tree.body)

        # Check if the code has any top-level expressions or calls that might act as an entry point.
        # Ignore tracker-injected calls (_big_o_tracker.*) since they are not real entry points.
        has_top_level_call = False
        last_function_name = None
        function_names: list[str] = []

        def _is_tracker_call(node: ast.stmt) -> bool:
            """Return True if the node is an injected _big_o_tracker.* call."""
            if not isinstance(node, ast.Expr):
                return False
            call = node.value
            if not isinstance(call, ast.Call):
                return False
            func = call.func
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                return func.value.id == "_big_o_tracker"
            return False

        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                last_function_name = node.name
                function_names.append(node.name)
            elif isinstance(node, (ast.Expr, ast.Call)) and not _is_tracker_call(node):
                has_top_level_call = True

        auto_entry_code = ""
        # If no top-level call found, inject a caller that reads from stdin.
        # Priority: forced_entry_point > "run" convention > last defined function.
        if not has_top_level_call and last_function_name:
            if forced_entry_point and forced_entry_point in function_names:
                entry_name = forced_entry_point
            elif "run" in function_names:
                entry_name = "run"
            else:
                entry_name = last_function_name
            auto_entry_code = f"""
import sys as _big_o_sys
import json as _big_o_json
try:
    _raw_input = _big_o_sys.stdin.read().strip()
    if _raw_input:
        try:
            _decoded_input = _big_o_json.loads(_raw_input)
        except _big_o_json.JSONDecodeError:
            _decoded_input = _raw_input
        {entry_name}(_decoded_input)
except Exception:
    pass
"""

        runtime_prelude = ast.parse(TRACKER_RUNTIME_SOURCE, mode="exec").body
        emit_metrics = ast.parse("__big_o_emit_metrics()", mode="exec").body
        
        if auto_entry_code:
            auto_entry_ast = ast.parse(auto_entry_code, mode="exec").body
            body.extend(auto_entry_ast)
            
        wrapped_body = ast.Try(
            body=body,
            handlers=[],
            orelse=[],
            finalbody=emit_metrics,
        )
        tree.body = [*prologue, *runtime_prelude, wrapped_body]
        ast.fix_missing_locations(tree)
        return ast.unparse(tree)

    @classmethod
    def _extract_instrumentation(cls, stderr: str, metadata) -> tuple[str, ExecutionInstrumentationReport | None]:
        marker_index = stderr.rfind(INSTRUMENTATION_MARKER)
        if marker_index == -1:
            return stderr, None

        metrics_payload = stderr[marker_index + len(INSTRUMENTATION_MARKER):].strip()
        cleaned_stderr = stderr[:marker_index].rstrip()
        if "\n" in metrics_payload:
            metrics_payload = metrics_payload.splitlines()[0].strip()

        try:
            parsed = json.loads(metrics_payload)
        except json.JSONDecodeError:
            return stderr, None

        line_counts = {
            int(line_no): int(count)
            for line_no, count in parsed.get("line_counts", {}).items()
        }
        function_call_counts = {
            str(name): int(count)
            for name, count in parsed.get("function_call_counts", {}).items()
        }
        loop_iteration_counts = {
            str(name): int(count)
            for name, count in parsed.get("loop_iteration_counts", {}).items()
        }

        report = ExecutionInstrumentationReport(
            line_counts=line_counts,
            function_call_counts=function_call_counts,
            loop_iteration_counts=loop_iteration_counts,
            line_numbers=list(metadata.line_numbers),
            function_names=list(metadata.function_names),
            loop_line_numbers=list(metadata.loop_line_numbers),
        )
        return cleaned_stderr, report
