from __future__ import annotations

from math import log
from typing import Iterable

from app.core.runtime import cached_call
from app.core.settings import get_settings
from app.schemas.explanation import ExplanationRequest, ExplanationResponse, ExplanationSection
from app.schemas.metrics import AggregatedFunctionMetric, AggregatedLineMetric, MetricPoint


class ExplanationService:
    SUPERLINEAR_CLASSES = {"O(n log n)", "O(n^2)", "O(n^3)", "O(2^n)"}

    @classmethod
    def generate(cls, payload: ExplanationRequest) -> ExplanationResponse:
        settings = get_settings()

        def factory() -> dict:
            return cls._generate_uncached(payload).model_dump()

        cached_payload, _ = cached_call(
            "explanations",
            payload.model_dump(mode="json"),
            ttl_seconds=settings.cache_analysis_ttl_seconds,
            factory=factory,
        )
        return ExplanationResponse.model_validate(cached_payload)

    @classmethod
    def _generate_uncached(cls, payload: ExplanationRequest) -> ExplanationResponse:
        snapshot = payload.metrics_snapshot
        summary = snapshot.summary

        dominant_line = cls._dominant_line(snapshot.line_metrics)
        dominant_function = cls._dominant_function(snapshot.function_metrics)
        complexity_class = payload.complexity_estimate.estimated_class if payload.complexity_estimate else None
        confidence = payload.complexity_estimate.confidence if payload.complexity_estimate else None

        growth_text, growth_kind = cls._describe_growth(summary.runtime_series.points, complexity_class)
        headline = cls._build_headline(growth_text, dominant_line, dominant_function)

        sections = [
            ExplanationSection(
                kind="summary",
                title="What the trace shows",
                body=cls._build_summary_text(growth_text, dominant_line, dominant_function),
                evidence=cls._summary_evidence(summary.runtime_series.points),
            )
        ]

        if dominant_line is not None:
            sections.append(
                ExplanationSection(
                    kind="dominance",
                    title="Dominant line",
                    body=cls._build_dominant_line_text(dominant_line),
                    evidence=cls._line_evidence(dominant_line),
                )
            )

        loop_section = cls._build_loop_section(snapshot.line_metrics, growth_kind)
        if loop_section is not None:
            sections.append(loop_section)

        if dominant_function is not None:
            sections.append(
                ExplanationSection(
                    kind="dominance",
                    title="Function hotspot",
                    body=cls._build_function_text(dominant_function),
                    evidence=cls._function_evidence(dominant_function),
                )
            )

        if complexity_class is not None:
            sections.append(
                ExplanationSection(
                    kind="complexity",
                    title="Complexity signal",
                    body=cls._build_complexity_text(complexity_class, confidence, growth_kind),
                    evidence=cls._complexity_evidence(payload),
                )
            )

        caveats = cls._build_caveats(payload, summary.runtime_series.points, snapshot.line_metrics, snapshot.function_metrics)
        if caveats:
            sections.append(
                ExplanationSection(
                    kind="caveat",
                    title="Caveats",
                    body=" ".join(caveats),
                    evidence=caveats,
                )
            )

        sections = sections[: payload.max_sections]

        return ExplanationResponse(
            headline=headline,
            summary=cls._build_summary_text(growth_text, dominant_line, dominant_function),
            complexity_class=complexity_class,
            confidence=confidence,
            dominant_line_number=dominant_line.line_number if dominant_line else None,
            dominant_function_name=dominant_function.function_name if dominant_function else None,
            sections=sections,
            caveats=caveats,
        )

    @staticmethod
    def _dominant_line(lines: Iterable[AggregatedLineMetric]) -> AggregatedLineMetric | None:
        ranked = sorted(
            lines,
            key=lambda item: (item.total_execution_count, item.total_time_ms, -item.line_number),
            reverse=True,
        )
        return ranked[0] if ranked else None

    @staticmethod
    def _dominant_function(functions: Iterable[AggregatedFunctionMetric]) -> AggregatedFunctionMetric | None:
        ranked = sorted(
            functions,
            key=lambda item: (item.total_call_count, item.total_time_ms, item.self_time_ms, item.function_name),
            reverse=True,
        )
        return ranked[0] if ranked else None

    @classmethod
    def _describe_growth(cls, points: list[MetricPoint], complexity_class: str | None) -> tuple[str, str]:
        if complexity_class is not None:
            if complexity_class in cls.SUPERLINEAR_CLASSES:
                return f"runtime scales faster than linear and fits {complexity_class}", "superlinear"
            if complexity_class == "O(n)":
                return "runtime grows roughly in line with input size", "linear"
            if complexity_class == "O(log n)":
                return "runtime increases slowly as input grows", "sublinear"
            if complexity_class == "O(1)":
                return "runtime stays mostly flat as input grows", "constant"

        inferred_kind = cls._infer_growth_kind(points)
        if inferred_kind == "superlinear":
            return "runtime grows faster than the input size", inferred_kind
        if inferred_kind == "linear":
            return "runtime grows proportionally with input size", inferred_kind
        if inferred_kind == "sublinear":
            return "runtime grows slowly compared with input size", inferred_kind
        return "runtime is too sparse to classify confidently", "unknown"

    @staticmethod
    def _infer_growth_kind(points: list[MetricPoint]) -> str:
        if len(points) < 2:
            return "unknown"
        first = points[0]
        last = points[-1]
        if first.input_size <= 0 or first.value <= 0 or last.value <= 0:
            return "unknown"

        size_ratio = last.input_size / first.input_size
        value_ratio = last.value / first.value
        if size_ratio <= 1:
            return "unknown"

        exponent = log(value_ratio) / log(size_ratio)
        if exponent >= 1.2:
            return "superlinear"
        if exponent >= 0.7:
            return "linear"
        return "sublinear"

    @staticmethod
    def _build_headline(
        growth_text: str,
        dominant_line: AggregatedLineMetric | None,
        dominant_function: AggregatedFunctionMetric | None,
    ) -> str:
        focus = []
        if dominant_line is not None:
            focus.append(f"line {dominant_line.line_number}")
        if dominant_function is not None:
            focus.append(f"function {dominant_function.function_name}")
        focus_text = " and ".join(focus) if focus else "the measured code"
        return f"{growth_text.capitalize()} with the main cost concentrated in {focus_text}."

    @staticmethod
    def _build_summary_text(
        growth_text: str,
        dominant_line: AggregatedLineMetric | None,
        dominant_function: AggregatedFunctionMetric | None,
    ) -> str:
        parts = [growth_text.capitalize() + "."]
        if dominant_line is not None:
            parts.append(
                f"Line {dominant_line.line_number} accounts for {dominant_line.total_execution_count} executions "
                f"and {dominant_line.percentage_of_total:.1%} of the measured line activity."
            )
        if dominant_function is not None:
            parts.append(
                f"Function {dominant_function.function_name} was called {dominant_function.total_call_count} times "
                f"and is the main function-level hotspot."
            )
        return " ".join(parts)

    @staticmethod
    def _build_dominant_line_text(line: AggregatedLineMetric) -> str:
        fragments = [
            f"Line {line.line_number} is the hottest line in the trace.",
            f"It executed {line.total_execution_count} times and represents {line.percentage_of_total:.1%} of total line activity.",
        ]
        if line.loop_iterations > 0:
            fragments.append(f"The line also carried {line.loop_iterations} loop iterations, which can multiply work as input grows.")
        if line.nesting_depth >= 2:
            fragments.append("Its nesting depth suggests repeated work inside another loop or branch.")
        return " ".join(fragments)

    @staticmethod
    def _build_function_text(function: AggregatedFunctionMetric) -> str:
        fragments = [
            f"Function {function.function_name} dominates the function-level trace with {function.total_call_count} calls.",
        ]
        if function.is_recursive or function.max_depth >= 2:
            fragments.append("Its call pattern suggests recursion or deep nesting may be contributing to growth.")
        return " ".join(fragments)

    @classmethod
    def _build_loop_section(
        cls,
        lines: list[AggregatedLineMetric],
        growth_kind: str,
    ) -> ExplanationSection | None:
        loop_lines = [line for line in lines if line.loop_iterations > 0 or line.nesting_depth > 0]
        if not loop_lines:
            return None

        loop_lines.sort(key=lambda item: (item.loop_iterations, item.nesting_depth, item.total_execution_count), reverse=True)
        top = loop_lines[0]
        body = (
            f"Loop activity is visible on line {top.line_number}, where {top.loop_iterations} loop iterations were recorded. "
            f"That repeated work is consistent with {growth_kind if growth_kind != 'unknown' else 'repeated'} growth."
        )
        evidence = [f"line {line.line_number}: loops={line.loop_iterations}, nesting={line.nesting_depth}" for line in loop_lines[:3]]
        return ExplanationSection(kind="loop", title="Loop behavior", body=body, evidence=evidence)

    @staticmethod
    def _build_complexity_text(
        complexity_class: str,
        confidence: float | None,
        growth_kind: str,
    ) -> str:
        confidence_text = f" with confidence {confidence:.2f}" if confidence is not None else ""
        if complexity_class in ExplanationService.SUPERLINEAR_CLASSES:
            reason = "That usually points to nested loops, repeated scans, or recursion that multiplies work."
        elif complexity_class == "O(n)":
            reason = "The measured work appears proportional to the input size."
        elif complexity_class == "O(log n)":
            reason = "The measured work rises slowly compared with input growth."
        else:
            reason = "The observed growth is not strong enough to infer a more specific structural cause."
        if growth_kind == "superlinear":
            reason = "The runtime curve accelerates as input grows, which is consistent with repeated work or nested iteration."
        return f"Estimated complexity: {complexity_class}{confidence_text}. {reason}"

    @staticmethod
    def _build_caveats(
        payload: ExplanationRequest,
        runtime_points: list[MetricPoint],
        line_metrics: list[AggregatedLineMetric],
        function_metrics: list[AggregatedFunctionMetric],
    ) -> list[str]:
        caveats: list[str] = []
        confidence = payload.complexity_estimate.confidence if payload.complexity_estimate else None
        sample_count = payload.complexity_estimate.sample_count if payload.complexity_estimate else len(runtime_points)

        if len(runtime_points) < 3:
            caveats.append("Only a small number of runtime samples were provided, so the growth trend may be unstable.")
        if confidence is not None and confidence < 0.7:
            caveats.append("The complexity fit has moderate confidence, so the estimate should be treated as a hint rather than a conclusion.")
        if payload.complexity_estimate and payload.complexity_estimate.estimated_class in ExplanationService.SUPERLINEAR_CLASSES:
            caveats.append("Superlinear fits can be sensitive to the selected input range, so the estimate should be validated with more sizes.")
        if sample_count < 4:
            caveats.append("More input sizes would improve the confidence of the estimate.")
        if not line_metrics:
            caveats.append("No line-level metrics were provided, so the explanation cannot pinpoint the hottest source line.")
        if not function_metrics:
            caveats.append("No function-level metrics were provided, so the explanation cannot identify a function hotspot.")
        return caveats

    @staticmethod
    def _summary_evidence(points: list[MetricPoint]) -> list[str]:
        if not points:
            return []
        first = points[0]
        last = points[-1]
        return [
            f"runtime series starts at n={first.input_size}, value={first.value}",
            f"runtime series ends at n={last.input_size}, value={last.value}",
        ]

    @staticmethod
    def _line_evidence(line: AggregatedLineMetric) -> list[str]:
        return [
            f"line {line.line_number} executions={line.total_execution_count}",
            f"line {line.line_number} share={line.percentage_of_total:.1%}",
        ]

    @staticmethod
    def _function_evidence(function: AggregatedFunctionMetric) -> list[str]:
        return [
            f"function {function.function_name} calls={function.total_call_count}",
            f"function {function.function_name} self_time_ms={function.self_time_ms}",
        ]

    @staticmethod
    def _complexity_evidence(payload: ExplanationRequest) -> list[str]:
        estimate = payload.complexity_estimate
        if estimate is None:
            return []
        return [
            f"best fit={estimate.estimated_class}",
            f"confidence={estimate.confidence:.2f}",
            f"samples={estimate.sample_count}",
        ]


__all__ = ["ExplanationService"]
