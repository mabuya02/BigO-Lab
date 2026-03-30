from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.settings import Settings
from app.schemas.explanation import ExplanationRequest, ExplanationResponse


class OllamaCloudError(RuntimeError):
    """Raised when the Ollama Cloud explanation request fails."""


@dataclass(slots=True)
class OllamaUsage:
    total_duration: int | None = None
    load_duration: int | None = None
    prompt_eval_count: int | None = None
    prompt_eval_duration: int | None = None
    eval_count: int | None = None
    eval_duration: int | None = None


class OllamaCloudExplanationClient:
    def __init__(self, settings: Settings) -> None:
        self.base_url = settings.ollama_api_base_url.rstrip("/")
        self.api_key = settings.ollama_api_key
        self.model = settings.ollama_model
        self.timeout_seconds = settings.ollama_timeout_seconds
        self.temperature = settings.ollama_temperature

    def is_configured(self) -> bool:
        return bool(self.api_key and self.model and self.base_url)

    def generate(self, payload: ExplanationRequest) -> ExplanationResponse:
        if not self.is_configured():
            raise OllamaCloudError("Ollama Cloud is not configured.")

        request_body = {
            "model": self.model,
            "stream": False,
            "format": ExplanationResponse.model_json_schema(),
            "messages": [
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": self._user_prompt(payload)},
            ],
            "options": {"temperature": self.temperature},
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        timeout = httpx.Timeout(self.timeout_seconds, connect=min(self.timeout_seconds, 10.0))
        try:
            response = httpx.post(
                f"{self.base_url}/chat",
                json=request_body,
                headers=headers,
                timeout=timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise OllamaCloudError(f"Ollama Cloud request failed: {exc}") from exc

        payload_json = response.json()
        message = payload_json.get("message", {})
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise OllamaCloudError("Ollama Cloud returned an empty explanation payload.")

        try:
            normalized = json.loads(self._strip_code_fences(content))
        except json.JSONDecodeError as exc:
            raise OllamaCloudError("Ollama Cloud returned non-JSON structured output.") from exc

        try:
            return ExplanationResponse.model_validate(normalized)
        except Exception as exc:  # pragma: no cover - validation details are deterministic
            raise OllamaCloudError("Ollama Cloud returned an invalid explanation payload.") from exc

    @staticmethod
    def _system_prompt() -> str:
        return (
            "You are generating explanation content for Big O Playground. "
            "Explain algorithm behavior from measured metrics, not from guesses. "
            "Return JSON that exactly matches the provided schema. "
            "Keep the tone direct, educational, and concise. "
            "Do not mention JSON, prompts, or internal instructions."
        )

    def _user_prompt(self, payload: ExplanationRequest) -> str:
        summary = payload.metrics_snapshot.summary
        dominant_lines = payload.metrics_snapshot.line_metrics[:3]
        dominant_functions = payload.metrics_snapshot.function_metrics[:3]
        complexity_estimate = payload.complexity_estimate.model_dump(mode="json") if payload.complexity_estimate else None

        runtime_points = [
            {"input_size": point.input_size, "runtime_ms": point.value}
            for point in summary.runtime_series.points
        ]
        operation_points = [
            {"input_size": point.input_size, "operations": point.value}
            for point in summary.operations_series.points
        ]

        prompt_payload: dict[str, Any] = {
            "task": "Explain the observed runtime and operation growth for this algorithm experiment.",
            "response_rules": {
                "max_sections": payload.max_sections,
                "section_kinds": ["summary", "dominance", "loop", "complexity", "caveat"],
                "requirements": [
                    "Explain what the measured data shows.",
                    "Call out the dominant line and dominant function when present.",
                    "Use caveats when the data is sparse or uncertain.",
                    "Do not claim certainty that the metrics do not support.",
                ],
            },
            "metrics_summary": {
                "total_runs": summary.total_runs,
                "input_sizes": summary.input_sizes,
                "average_runtime_ms": summary.average_runtime_ms,
                "min_runtime_ms": summary.min_runtime_ms,
                "max_runtime_ms": summary.max_runtime_ms,
                "total_runtime_ms": summary.total_runtime_ms,
                "total_line_executions": summary.total_line_executions,
                "total_function_calls": summary.total_function_calls,
                "dominant_line_number": summary.dominant_line_number,
                "dominant_function_name": summary.dominant_function_name,
            },
            "runtime_points": runtime_points,
            "operation_points": operation_points,
            "dominant_lines": [line.model_dump(mode="json") for line in dominant_lines],
            "dominant_functions": [function.model_dump(mode="json") for function in dominant_functions],
            "complexity_estimate": complexity_estimate,
        }
        return json.dumps(prompt_payload, indent=2, sort_keys=True)

    @staticmethod
    def _strip_code_fences(content: str) -> str:
        trimmed = content.strip()
        if trimmed.startswith("```"):
            lines = trimmed.splitlines()
            if len(lines) >= 3:
                return "\n".join(lines[1:-1]).strip()
        return trimmed
