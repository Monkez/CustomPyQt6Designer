from __future__ import annotations

import unittest

from monkez_pyqt6.monkez_canva import (
    PaletteEntry,
    normalize_component_ids,
    record_recent_component,
    search_palette,
)


class CanvasPaletteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.entries = (
            PaletteEntry("rectangle", "Rectangle", "Shapes", keywords=("box",)),
            PaletteEntry("line_chart", "Line chart", "Diagram & data", keywords=("plot",)),
            PaletteEntry("bar_chart", "Bar chart", "Diagram & data", keywords=("plot",)),
            PaletteEntry("image", "Image", "Media", keywords=("picture",)),
        )

    def test_search_uses_label_type_category_and_keywords(self) -> None:
        self.assertEqual(
            ("line_chart", "bar_chart"),
            tuple(entry.type_id for entry in search_palette(self.entries, "chart")),
        )
        self.assertEqual(
            ("rectangle",),
            tuple(entry.type_id for entry in search_palette(self.entries, "box")),
        )
        self.assertEqual(
            ("image",),
            tuple(entry.type_id for entry in search_palette(self.entries, category="Media")),
        )

    def test_favorites_and_recent_have_explicit_order(self) -> None:
        favorites = search_palette(
            self.entries, category="favorites", favorites=("bar_chart", "rectangle")
        )
        recent = search_palette(
            self.entries, category="recent", recent=("image", "line_chart")
        )
        self.assertEqual(("bar_chart", "rectangle"), tuple(item.type_id for item in favorites))
        self.assertEqual(("image", "line_chart"), tuple(item.type_id for item in recent))

    def test_preference_normalization_and_recent_limit(self) -> None:
        self.assertEqual(("node", "line"), normalize_component_ids((" Node ", "node", "LINE")))
        recent = ()
        for index in range(15):
            recent = record_recent_component(recent, f"type-{index}", limit=4)
        self.assertEqual(("type-14", "type-13", "type-12", "type-11"), recent)


if __name__ == "__main__":
    unittest.main()
