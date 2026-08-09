from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from monkez_pyqt6.monkez_canva import (
    ASSET_MANIFEST_KEY,
    atomic_write_json,
    backup_path,
    build_asset_manifest,
    load_json_with_recovery,
    verify_asset_manifest,
)


class CanvasPersistenceTests(unittest.TestCase):
    def test_atomic_write_preserves_last_valid_document_as_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "workspace.json"
            first = {"format": "monkez-canva", "version": 1, "value": "first"}
            second = {"format": "monkez-canva", "version": 1, "value": "second"}

            atomic_write_json(target, first)
            atomic_write_json(target, second)

            self.assertEqual(second, json.loads(target.read_text(encoding="utf-8")))
            self.assertEqual(first, json.loads(backup_path(target).read_text(encoding="utf-8")))
            self.assertFalse(list(target.parent.glob("*.tmp")))

    def test_corrupt_primary_recovers_from_backup_without_overwriting_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "workspace.json"
            previous = {"format": "monkez-canva", "version": 1, "value": "safe"}
            atomic_write_json(target, previous)
            atomic_write_json(target, {**previous, "value": "latest"})
            target.write_text('{"truncated":', encoding="utf-8")

            loaded = load_json_with_recovery(target)

            self.assertTrue(loaded.recovered_from_backup)
            self.assertEqual(previous, loaded.payload)
            self.assertEqual(backup_path(target), loaded.source)
            self.assertIn("JSONDecodeError", loaded.primary_error)
            self.assertEqual(previous, json.loads(backup_path(target).read_text(encoding="utf-8")))

    def test_asset_manifest_detects_tampering_missing_and_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asset = root / "assets" / "image.png"
            asset.parent.mkdir()
            asset.write_bytes(b"original")
            document = {
                "scene": {"backgroundImage": "assets/image.png"},
                "elements": [],
                "connectors": [{"id": "edge", "source": "node-a", "target": "node-b"}],
                "resources": [],
            }
            document[ASSET_MANIFEST_KEY] = build_asset_manifest(document, root)
            self.assertFalse(verify_asset_manifest(document, root))

            asset.write_bytes(b"changed")
            issues = verify_asset_manifest(document, root)
            self.assertEqual("checksum mismatch", issues[0].reason)

            escaped = dict(document)
            escaped["scene"] = {"backgroundImage": "../outside.png"}
            escaped[ASSET_MANIFEST_KEY] = {"../outside.png": {"sha256": "x"}}
            self.assertEqual(
                "path escapes the project workspace",
                verify_asset_manifest(escaped, root)[0].reason,
            )


if __name__ == "__main__":
    unittest.main()
