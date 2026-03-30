from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
import unittest


def _load_complexity_service():
    service_path = Path(__file__).resolve().parents[2] / "app" / "services" / "complexity_service.py"
    spec = importlib.util.spec_from_file_location("complexity_service_under_test", service_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load complexity service module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.ComplexityService


ComplexityService = _load_complexity_service()


class ComplexityServiceTests(unittest.TestCase):
    def test_detects_linear_growth(self) -> None:
        samples = [
            {"input_size": 5, "runtime_ms": 15},
            {"input_size": 10, "runtime_ms": 25},
            {"input_size": 20, "runtime_ms": 45},
            {"input_size": 40, "runtime_ms": 85},
            {"input_size": 80, "runtime_ms": 165},
        ]

        analysis = ComplexityService.estimate_complexity(samples)

        self.assertEqual(analysis.estimated_class, "O(n)")
        self.assertGreater(analysis.confidence, 0.6)
        self.assertIn("Best fit: O(n)", analysis.explanation)
        self.assertGreaterEqual(len(analysis.alternatives), 2)

    def test_detects_logarithmic_growth(self) -> None:
        samples = [
            {"input_size": 2, "runtime_ms": 5},
            {"input_size": 4, "runtime_ms": 8},
            {"input_size": 8, "runtime_ms": 11},
            {"input_size": 16, "runtime_ms": 14},
            {"input_size": 32, "runtime_ms": 17},
            {"input_size": 64, "runtime_ms": 20},
        ]

        analysis = ComplexityService.estimate_complexity(samples)

        self.assertEqual(analysis.estimated_class, "O(log n)")
        self.assertGreater(analysis.confidence, 0.6)
        self.assertIn("O(log n)", analysis.explanation)

    def test_detects_quadratic_growth(self) -> None:
        samples = [
            {"input_size": 1, "runtime_ms": 1},
            {"input_size": 2, "runtime_ms": 4},
            {"input_size": 3, "runtime_ms": 9},
            {"input_size": 4, "runtime_ms": 16},
            {"input_size": 5, "runtime_ms": 25},
            {"input_size": 6, "runtime_ms": 36},
        ]

        analysis = ComplexityService.estimate_complexity(samples)

        self.assertEqual(analysis.estimated_class, "O(n^2)")
        self.assertGreater(analysis.confidence, 0.6)
        self.assertTrue(any(candidate.big_o == "O(n^3)" for candidate in analysis.alternatives))

    def test_detects_exponential_growth(self) -> None:
        samples = [
            {"input_size": 1, "runtime_ms": 2},
            {"input_size": 2, "runtime_ms": 4},
            {"input_size": 3, "runtime_ms": 8},
            {"input_size": 4, "runtime_ms": 16},
            {"input_size": 5, "runtime_ms": 32},
            {"input_size": 6, "runtime_ms": 64},
        ]

        analysis = ComplexityService.estimate_complexity(samples)

        self.assertEqual(analysis.estimated_class, "O(2^n)")
        self.assertGreater(analysis.confidence, 0.6)
        self.assertIn("Confidence", analysis.explanation)

    def test_to_model_preserves_analysis_payload(self) -> None:
        analysis = ComplexityService.estimate_complexity(
            [
                {"input_size": 3, "runtime_ms": 9},
                {"input_size": 6, "runtime_ms": 36},
                {"input_size": 9, "runtime_ms": 81},
            ]
        )
        payload = ComplexityService.to_model(analysis, experiment_id="exp-123")

        self.assertEqual(payload["experiment_id"], "exp-123")
        self.assertEqual(payload["estimated_class"], analysis.estimated_class)
        self.assertEqual(payload["sample_count"], analysis.sample_count)
        self.assertEqual(payload["alternatives"][0]["big_o"], analysis.alternatives[0].big_o)
