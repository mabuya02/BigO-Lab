from __future__ import annotations

from dataclasses import asdict, dataclass
from math import exp, isfinite, log2, sqrt
from statistics import fmean
from typing import Any, Iterable, Mapping, Sequence

from app.utils.helpers import utcnow


@dataclass(frozen=True, slots=True)
class ComplexitySample:
    input_size: float
    value: float


@dataclass(frozen=True, slots=True)
class ComplexityFit:
    label: str
    big_o: str
    quality: float
    rmse: float
    normalized_rmse: float
    slope: float
    intercept: float
    valid: bool
    notes: str


@dataclass(frozen=True, slots=True)
class ComplexityAnalysis:
    estimated_class: str
    confidence: float
    sample_count: int
    metric_name: str
    explanation: str
    alternatives: list[ComplexityFit]
    evidence: dict[str, Any]
    created_at: Any | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["alternatives"] = [asdict(item) for item in self.alternatives]
        return payload


class ComplexityService:
    CANDIDATES = (
        ("constant", "O(1)"),
        ("logarithmic", "O(log n)"),
        ("linear", "O(n)"),
        ("linearithmic", "O(n log n)"),
        ("quadratic", "O(n^2)"),
        ("cubic", "O(n^3)"),
        ("exponential", "O(2^n)"),
    )

    @classmethod
    def estimate_complexity(
        cls,
        runs: Sequence[Mapping[str, Any] | Any],
        *,
        metric_name: str = "runtime_ms",
        size_key: str = "input_size",
        value_key: str | None = None,
        experiment_id: str | None = None,
    ) -> ComplexityAnalysis:
        samples = cls._normalize_samples(
            runs,
            size_key=size_key,
            value_key=value_key or metric_name,
        )
        if not samples:
            raise ValueError("At least one sample is required to estimate complexity")

        fits = [fit for fit in (cls._fit_candidate(samples, label, big_o) for label, big_o in cls.CANDIDATES) if fit.valid]
        if not fits:
            raise ValueError("Unable to fit any complexity class to the provided samples")

        fits.sort(key=lambda item: item.quality, reverse=True)
        best = fits[0]
        runner_up = fits[1] if len(fits) > 1 else None
        confidence = cls._compute_confidence(best, runner_up, len(samples))
        explanation = cls._build_explanation(best, runner_up, samples, metric_name, confidence)

        evidence = {
            "sample_count": len(samples),
            "best_quality": best.quality,
            "best_rmse": best.rmse,
            "best_normalized_rmse": best.normalized_rmse,
            "value_range": cls._value_range(samples),
            "input_range": cls._input_range(samples),
            "experiment_id": experiment_id,
        }

        alternatives = fits[1:4]
        return ComplexityAnalysis(
            estimated_class=best.big_o,
            confidence=confidence,
            sample_count=len(samples),
            metric_name=metric_name,
            explanation=explanation,
            alternatives=alternatives,
            evidence=evidence,
            created_at=utcnow(),
        )

    @classmethod
    def to_model(
        cls,
        analysis: ComplexityAnalysis,
        *,
        experiment_id: str | None = None,
    ) -> dict[str, Any]:
        return {
            "experiment_id": experiment_id,
            "metric_name": analysis.metric_name,
            "estimated_class": analysis.estimated_class,
            "confidence": analysis.confidence,
            "sample_count": analysis.sample_count,
            "explanation": analysis.explanation,
            "alternatives": [asdict(candidate) for candidate in analysis.alternatives],
            "evidence": analysis.evidence,
            "created_at": analysis.created_at,
            "updated_at": utcnow(),
        }

    @classmethod
    def _normalize_samples(
        cls,
        runs: Sequence[Mapping[str, Any] | Any],
        *,
        size_key: str,
        value_key: str,
    ) -> list[ComplexitySample]:
        samples: list[ComplexitySample] = []
        for run in runs:
            size = cls._extract_number(run, size_key, fallback_keys=("n", "size", "input", "input_size"))
            value = cls._extract_number(run, value_key, fallback_keys=("value", "runtime_ms", "operations", "count"))
            if size is None or value is None:
                continue
            if size <= 0:
                continue
            if not (isfinite(size) and isfinite(value)):
                continue
            samples.append(ComplexitySample(input_size=float(size), value=float(value)))
        samples.sort(key=lambda item: item.input_size)
        return samples

    @classmethod
    def _extract_number(
        cls,
        item: Mapping[str, Any] | Any,
        key: str,
        *,
        fallback_keys: Sequence[str] = (),
    ) -> float | None:
        candidate_keys = (key, *fallback_keys)
        for candidate in candidate_keys:
            raw_value = cls._read_value(item, candidate)
            if raw_value is None:
                continue
            try:
                return float(raw_value)
            except (TypeError, ValueError):
                continue
        return None

    @staticmethod
    def _read_value(item: Mapping[str, Any] | Any, key: str) -> Any:
        if isinstance(item, Mapping):
            return item.get(key)
        return getattr(item, key, None)

    @classmethod
    def _fit_candidate(cls, samples: Sequence[ComplexitySample], label: str, big_o: str) -> ComplexityFit:
        transformed = cls._transform_samples(samples, label)
        if transformed is None:
            return ComplexityFit(
                label=label,
                big_o=big_o,
                quality=0.0,
                rmse=float("inf"),
                normalized_rmse=float("inf"),
                slope=0.0,
                intercept=0.0,
                valid=False,
                notes="Insufficient sample shape for this candidate",
            )

        x_values, y_values = transformed
        if label == "exponential":
            return cls._fit_exponential(samples, big_o)

        slope, intercept = cls._linear_regression(x_values, y_values)
        predictions = [slope * x + intercept for x in x_values]
        return cls._build_fit(label, big_o, y_values, predictions, slope, intercept)

    @classmethod
    def _fit_exponential(cls, samples: Sequence[ComplexitySample], big_o: str) -> ComplexityFit:
        if any(sample.value <= 0 for sample in samples):
            return ComplexityFit(
                label="exponential",
                big_o=big_o,
                quality=0.0,
                rmse=float("inf"),
                normalized_rmse=float("inf"),
                slope=0.0,
                intercept=0.0,
                valid=False,
                notes="Exponential fitting requires strictly positive values",
            )

        x_values = [sample.input_size for sample in samples]
        log_values = [log2(sample.value) for sample in samples]
        slope, intercept = cls._linear_regression(x_values, log_values)
        predictions = [2 ** (slope * x + intercept) for x in x_values]
        return cls._build_fit("exponential", big_o, [sample.value for sample in samples], predictions, slope, intercept)

    @classmethod
    def _build_fit(
        cls,
        label: str,
        big_o: str,
        actual: Sequence[float],
        predicted: Sequence[float],
        slope: float,
        intercept: float,
    ) -> ComplexityFit:
        rmse = cls._root_mean_squared_error(actual, predicted)
        scale = max(fmean(actual), max(actual) - min(actual), 1.0)
        normalized_rmse = rmse / scale
        quality = 1.0 / (1.0 + normalized_rmse)
        return ComplexityFit(
            label=label,
            big_o=big_o,
            quality=quality,
            rmse=rmse,
            normalized_rmse=normalized_rmse,
            slope=slope,
            intercept=intercept,
            valid=True,
            notes=cls._build_notes(label, actual, predicted),
        )

    @staticmethod
    def _build_notes(label: str, actual: Sequence[float], predicted: Sequence[float]) -> str:
        first_error = abs(actual[0] - predicted[0]) if actual else 0.0
        last_error = abs(actual[-1] - predicted[-1]) if actual else 0.0
        return f"{label} fit residuals start at {first_error:.3f} and end at {last_error:.3f}"

    @classmethod
    def _transform_samples(
        cls,
        samples: Sequence[ComplexitySample],
        label: str,
    ) -> tuple[list[float], list[float]] | None:
        if len(samples) < 2 and label != "constant":
            return None

        x_values = [sample.input_size for sample in samples]
        y_values = [sample.value for sample in samples]

        if label == "constant":
            return [1.0 for _ in samples], y_values
        if label == "logarithmic":
            if len({sample.input_size for sample in samples}) < 2:
                return None
            return [log2(sample.input_size) for sample in samples], y_values
        if label == "linear":
            return x_values, y_values
        if label == "linearithmic":
            if any(sample.input_size < 2 for sample in samples):
                return None
            return [sample.input_size * log2(sample.input_size) for sample in samples], y_values
        if label == "quadratic":
            return [sample.input_size**2 for sample in samples], y_values
        if label == "cubic":
            return [sample.input_size**3 for sample in samples], y_values
        if label == "exponential":
            return x_values, y_values
        return None

    @staticmethod
    def _linear_regression(x_values: Sequence[float], y_values: Sequence[float]) -> tuple[float, float]:
        x_mean = fmean(x_values)
        y_mean = fmean(y_values)
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        if denominator == 0:
            return 0.0, y_mean
        slope = numerator / denominator
        intercept = y_mean - slope * x_mean
        return slope, intercept

    @staticmethod
    def _root_mean_squared_error(actual: Sequence[float], predicted: Sequence[float]) -> float:
        if not actual:
            return float("inf")
        return sqrt(sum((a - p) ** 2 for a, p in zip(actual, predicted)) / len(actual))

    @staticmethod
    def _compute_confidence(best: ComplexityFit, runner_up: ComplexityFit | None, sample_count: int) -> float:
        separation = 0.0
        if runner_up is not None and best.quality > 0:
            separation = max(0.0, best.quality - runner_up.quality) / best.quality
        sample_factor = min(1.0, sample_count / 5.0)
        confidence = best.quality * (0.65 + 0.35 * separation) * (0.55 + 0.45 * sample_factor)
        return max(0.0, min(1.0, confidence))

    @staticmethod
    def _build_explanation(
        best: ComplexityFit,
        runner_up: ComplexityFit | None,
        samples: Sequence[ComplexitySample],
        metric_name: str,
        confidence: float,
    ) -> str:
        first = samples[0]
        last = samples[-1]
        observed_growth = last.value / first.value if first.value not in (0.0, -0.0) else float("inf")
        input_growth = last.input_size / first.input_size if first.input_size not in (0.0, -0.0) else float("inf")

        lines = [
            f"Best fit: {best.big_o} for {metric_name}.",
            f"The transformed residual error was lowest for the {best.label} candidate.",
            f"Across the observed range, input size grew by about {input_growth:.2f}x while {metric_name} grew by about {observed_growth:.2f}x.",
        ]
        if runner_up is not None:
            lines.append(
                f"The nearest alternative was {runner_up.big_o} with a lower quality score of {runner_up.quality:.3f}."
            )
        lines.append(f"Confidence is {'high' if confidence >= 0.8 else 'moderate' if confidence >= 0.5 else 'low'} at {confidence:.2f}.")
        lines.append(f"Residual note: {best.notes}.")
        return " ".join(lines)

    @staticmethod
    def _value_range(samples: Sequence[ComplexitySample]) -> dict[str, float]:
        values = [sample.value for sample in samples]
        return {"min": min(values), "max": max(values)}

    @staticmethod
    def _input_range(samples: Sequence[ComplexitySample]) -> dict[str, float]:
        sizes = [sample.input_size for sample in samples]
        return {"min": min(sizes), "max": max(sizes)}
