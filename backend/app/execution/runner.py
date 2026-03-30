from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Protocol

from app.execution.sandbox import SandboxExecutionResult, SandboxLimits

try:
    import resource
except ImportError:  # pragma: no cover - only relevant on non-Unix systems
    resource = None


class SandboxRunner(Protocol):
    backend_name: str

    def is_available(self) -> bool:
        ...

    def run(self, code: str, stdin: str, limits: SandboxLimits) -> SandboxExecutionResult:
        ...


def docker_cli_available() -> bool:
    return shutil.which("docker") is not None


def ensure_workspace_root(path: str) -> Path:
    workspace_root = Path(path)
    workspace_root.mkdir(parents=True, exist_ok=True)
    return workspace_root


def truncate_output(output: str, limit_bytes: int) -> tuple[str, bool]:
    encoded = output.encode("utf-8", errors="replace")
    if len(encoded) <= limit_bytes:
        return output, False
    trimmed = encoded[:limit_bytes].decode("utf-8", errors="replace")
    return f"{trimmed}\n...[truncated]", True


def _resource_limiter(limits: SandboxLimits):
    if resource is None:
        return None

    def apply_limits() -> None:
        memory_bytes = limits.memory_limit_mb * 1024 * 1024
        cpu_seconds = max(limits.timeout_seconds, 1) + 1
        limit_pairs = [
            (getattr(resource, "RLIMIT_AS", None), (memory_bytes, memory_bytes)),
            (getattr(resource, "RLIMIT_CPU", None), (cpu_seconds, cpu_seconds)),
            (getattr(resource, "RLIMIT_CORE", None), (0, 0)),
        ]
        if hasattr(resource, "RLIMIT_NPROC"):
            limit_pairs.append((resource.RLIMIT_NPROC, (32, 32)))

        for limit_name, value in limit_pairs:
            if limit_name is None:
                continue
            try:
                resource.setrlimit(limit_name, value)
            except Exception:
                continue

    return apply_limits


class LocalPythonRunner:
    backend_name = "local"

    def __init__(self, workspace_root: str) -> None:
        self.workspace_root = ensure_workspace_root(workspace_root)

    def is_available(self) -> bool:
        return True

    def run(self, code: str, stdin: str, limits: SandboxLimits) -> SandboxExecutionResult:
        with tempfile.TemporaryDirectory(prefix="big-o-local-", dir=self.workspace_root) as workspace:
            script_path = Path(workspace) / "main.py"
            script_path.write_text(code, encoding="utf-8")
            command = [sys.executable, str(script_path)]
            env = {
                "PATH": os.getenv("PATH", ""),
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONUNBUFFERED": "1",
            }
            start = time.perf_counter()
            try:
                completed = subprocess.run(
                    command,
                    input=stdin,
                    capture_output=True,
                    text=True,
                    cwd=workspace,
                    env=env,
                    timeout=limits.timeout_seconds,
                    preexec_fn=_resource_limiter(limits),
                )
            except subprocess.TimeoutExpired as exc:
                runtime_ms = int((time.perf_counter() - start) * 1000)
                stdout, truncated_stdout = truncate_output(exc.stdout or "", limits.output_limit_bytes)
                stderr, truncated_stderr = truncate_output(
                    f"{exc.stderr or ''}\nExecution timed out.".strip(),
                    limits.output_limit_bytes,
                )
                return SandboxExecutionResult(
                    status="timeout",
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=None,
                    runtime_ms=runtime_ms,
                    backend=self.backend_name,
                    timed_out=True,
                    truncated_stdout=truncated_stdout,
                    truncated_stderr=truncated_stderr,
                )

            runtime_ms = int((time.perf_counter() - start) * 1000)
            stdout, truncated_stdout = truncate_output(completed.stdout, limits.output_limit_bytes)
            stderr, truncated_stderr = truncate_output(completed.stderr, limits.output_limit_bytes)
            return SandboxExecutionResult(
                status="completed" if completed.returncode == 0 else "failed",
                stdout=stdout,
                stderr=stderr,
                exit_code=completed.returncode,
                runtime_ms=runtime_ms,
                backend=self.backend_name,
                truncated_stdout=truncated_stdout,
                truncated_stderr=truncated_stderr,
            )


class DockerPythonRunner:
    backend_name = "docker"

    def __init__(self, image: str, workspace_root: str) -> None:
        self.image = image
        self.workspace_root = ensure_workspace_root(workspace_root)

    def image_available(self) -> bool:
        if not docker_cli_available():
            return False
        inspection = subprocess.run(
            ["docker", "image", "inspect", self.image],
            capture_output=True,
            text=True,
        )
        return inspection.returncode == 0

    def is_available(self) -> bool:
        return docker_cli_available() and self.image_available()

    def run(self, code: str, stdin: str, limits: SandboxLimits) -> SandboxExecutionResult:
        if not docker_cli_available():
            raise RuntimeError("Docker CLI is not available on this host")
        if not self.image_available():
            raise RuntimeError(f"Docker sandbox image '{self.image}' is not available")

        with tempfile.TemporaryDirectory(prefix="big-o-docker-", dir=self.workspace_root) as workspace:
            script_path = Path(workspace) / "main.py"
            script_path.write_text(code, encoding="utf-8")
            command = [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--cpus",
                str(limits.cpu_limit),
                "--memory",
                f"{limits.memory_limit_mb}m",
                "--pids-limit",
                "64",
                "--read-only",
                "--security-opt",
                "no-new-privileges",
                "--cap-drop",
                "ALL",
                "--tmpfs",
                "/tmp:rw,noexec,nosuid,size=64m",
                "--workdir",
                "/workspace",
                "-v",
                f"{workspace}:/workspace:ro",
                "-e",
                "PYTHONDONTWRITEBYTECODE=1",
                "-e",
                "PYTHONUNBUFFERED=1",
                self.image,
                "python",
                "/workspace/main.py",
            ]

            start = time.perf_counter()
            try:
                completed = subprocess.run(
                    command,
                    input=stdin,
                    capture_output=True,
                    text=True,
                    timeout=limits.timeout_seconds + 1,
                )
            except subprocess.TimeoutExpired as exc:
                runtime_ms = int((time.perf_counter() - start) * 1000)
                stdout, truncated_stdout = truncate_output(exc.stdout or "", limits.output_limit_bytes)
                stderr, truncated_stderr = truncate_output(
                    f"{exc.stderr or ''}\nExecution timed out.".strip(),
                    limits.output_limit_bytes,
                )
                return SandboxExecutionResult(
                    status="timeout",
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=None,
                    runtime_ms=runtime_ms,
                    backend=self.backend_name,
                    timed_out=True,
                    truncated_stdout=truncated_stdout,
                    truncated_stderr=truncated_stderr,
                )

            runtime_ms = int((time.perf_counter() - start) * 1000)
            stdout, truncated_stdout = truncate_output(completed.stdout, limits.output_limit_bytes)
            stderr, truncated_stderr = truncate_output(completed.stderr, limits.output_limit_bytes)
            return SandboxExecutionResult(
                status="completed" if completed.returncode == 0 else "failed",
                stdout=stdout,
                stderr=stderr,
                exit_code=completed.returncode,
                runtime_ms=runtime_ms,
                backend=self.backend_name,
                truncated_stdout=truncated_stdout,
                truncated_stderr=truncated_stderr,
            )
