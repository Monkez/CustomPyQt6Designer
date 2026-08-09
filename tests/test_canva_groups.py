from __future__ import annotations

import unittest

from monkez_pyqt6.monkez_canva import (
    CanvasDocument,
    descendant_element_ids,
    group_bounds,
    normalize_group_kind,
    validate_group_graph,
)


class CanvasGroupTests(unittest.TestCase):
    def test_group_bounds_include_header_padding_and_minimum_size(self) -> None:
        self.assertEqual(
            (72.0, 34.0, 256.0, 164.0),
            group_bounds(((100, 100, 80, 40), (240, 120, 60, 50))),
        )
        self.assertEqual((0.0, 0.0, 180.0, 110.0), group_bounds(()))

    def test_nested_descendants_are_stable_and_unique(self) -> None:
        groups = {
            "root": {"id": "root", "members": ["a", "nested", "b"]},
            "nested": {"id": "nested", "members": ["b", "c"]},
        }
        self.assertEqual(
            ("a", "b", "c"),
            descendant_element_ids("root", groups, ("a", "b", "c")),
        )
        validate_group_graph(groups, ("a", "b", "c"))

    def test_group_graph_rejects_cycles_missing_members_and_unknown_kind(self) -> None:
        with self.assertRaisesRegex(ValueError, "cycle"):
            validate_group_graph(
                {
                    "first": {"members": ["second"]},
                    "second": {"members": ["first"]},
                },
                (),
            )
        with self.assertRaisesRegex(ValueError, "missing members"):
            validate_group_graph({"group": {"members": ["absent"]}}, ())
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            normalize_group_kind("mystery")

    def test_document_rejects_cycle_during_group_update(self) -> None:
        document = CanvasDocument.from_dict(
            {
                "format": "monkez-canva",
                "version": 1,
                "scene": {},
                "elements": [
                    {"id": "a", "type": "node"},
                    {"id": "b", "type": "node"},
                ],
            }
        )
        document.add_group({"id": "inner", "members": ["a"]})
        document.add_group({"id": "outer", "members": ["inner", "b"]})
        with self.assertRaisesRegex(ValueError, "cycle"):
            document.update_group("inner", {"members": ["outer"]})
        self.assertEqual(("a",), document.group("inner").members)
        events = document.rename_group("inner", "renamed")
        self.assertEqual("group.renamed", events[0].action)
        self.assertEqual(("renamed", "b"), document.group("outer").members)


if __name__ == "__main__":
    unittest.main()
