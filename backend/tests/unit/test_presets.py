from __future__ import annotations

import unittest

from app.services.preset_service import PresetService


class PresetServiceTests(unittest.TestCase):
    def test_lists_catalog_with_categories(self) -> None:
        catalog = PresetService.list_presets()
        self.assertGreaterEqual(len(catalog.presets), 4)
        self.assertGreaterEqual(len(catalog.categories), 4)
        self.assertTrue(any(preset.slug == "bubble-sort" for preset in catalog.presets))

    def test_get_preset_returns_expected_algorithm(self) -> None:
        preset = PresetService.get_preset("binary-search")
        self.assertEqual(preset.name, "Binary Search")
        self.assertEqual(preset.expected_complexity, "O(log n)")
        self.assertEqual(preset.category, "searching")

    def test_category_filter_only_returns_matching_presets(self) -> None:
        catalog = PresetService.list_presets(category="sorting")
        self.assertTrue(catalog.presets)
        self.assertTrue(all(preset.category == "sorting" for preset in catalog.presets))


if __name__ == "__main__":
    unittest.main()
