from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from monkez_pyqt6.monkez_canva import (
    PLUGIN_PACKAGE_FORMAT,
    PLUGIN_PACKAGE_VERSION,
    PluginPackageManifest,
    PluginTrustStore,
    discover_plugin_packages,
    load_trusted_plugin_package,
    unload_plugin_package,
)
from monkez_pyqt6.monkez_widgets import MonkezCanva


PLUGIN_SOURCE = '''
from pathlib import Path
from monkez_pyqt6.monkez_canva import ElementDefinition, component_plugin

Path(__file__).parent.parent.joinpath("executed.txt").write_text("loaded", encoding="utf-8")
PLUGIN = component_plugin(
    "com.example.packaged",
    "Packaged example",
    "1.2.0",
    (
        ElementDefinition(
            "packaged_sensor", "Packaged sensor", "Package tests", 160, 90,
            plugin_id="com.example.packaged",
            capabilities={"geometry", "appearance"},
        ),
    ),
)
'''


def write_package(
    root: Path,
    directory: str = "packaged",
    *,
    plugin_id: str = "com.example.packaged",
    entry_file: str = "plugin.py",
) -> Path:
    package = root / directory
    package.mkdir(parents=True)
    manifest = {
        "format": PLUGIN_PACKAGE_FORMAT,
        "version": PLUGIN_PACKAGE_VERSION,
        "pluginId": plugin_id,
        "label": "Packaged example",
        "pluginVersion": "1.2.0",
        "description": "Trusted package fixture",
        "author": "Example",
        "minimumSdk": 1,
        "entryPoint": {"file": entry_file, "symbol": "PLUGIN"},
        "componentTypes": ["packaged_sensor"],
        "metadata": {"channel": "tests"},
    }
    (package / "plugin.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if entry_file == "plugin.py":
        (package / entry_file).write_text(PLUGIN_SOURCE, encoding="utf-8")
    return package


class PluginPackageCoreTests(unittest.TestCase):
    def test_manifest_roundtrip_is_immutable_and_rejects_unsafe_entry(self) -> None:
        manifest = PluginPackageManifest.from_dict(
            {
                "format": PLUGIN_PACKAGE_FORMAT,
                "version": PLUGIN_PACKAGE_VERSION,
                "pluginId": "COM.Example.Packaged",
                "label": "Package",
                "pluginVersion": "2.0",
                "entryPoint": {"file": "plugin.py", "symbol": "PLUGIN"},
                "componentTypes": ["sensor", "sensor", "chart"],
                "metadata": {"vendor": "Example"},
            }
        )

        self.assertEqual("com.example.packaged", manifest.plugin_id)
        self.assertEqual(("sensor", "chart"), manifest.component_types)
        self.assertEqual(manifest.to_dict(), PluginPackageManifest.from_dict(manifest.to_dict()).to_dict())
        with self.assertRaises(TypeError):
            manifest.metadata["vendor"] = "Changed"
        invalid = manifest.to_dict()
        invalid["entryPoint"]["file"] = "../outside.py"
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            PluginPackageManifest.from_dict(invalid)

    def test_discovery_never_executes_and_exact_trust_allows_loading(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_package(root)
            store = PluginTrustStore()

            report = discover_plugin_packages(root, trust_store=store)
            candidate = report.candidates[0]
            self.assertEqual("untrusted", candidate.state)
            self.assertFalse((root / "executed.txt").exists())
            with self.assertRaisesRegex(PermissionError, "not trusted"):
                load_trusted_plugin_package(candidate, store)

            store.trust(candidate)
            trusted = discover_plugin_packages(root, trust_store=store).candidates[0]
            self.assertEqual("trusted", trusted.state)
            loaded = load_trusted_plugin_package(trusted, store)
            self.assertEqual("com.example.packaged", loaded.plugin.plugin_id)
            self.assertEqual(("packaged_sensor",), loaded.plugin.type_ids)
            self.assertEqual("loaded", loaded.candidate.state)
            self.assertTrue((root / "executed.txt").is_file())
            self.assertIn(loaded.module_name, sys.modules)
            unload_plugin_package(loaded)
            self.assertNotIn(loaded.module_name, sys.modules)

    def test_changed_package_invalidates_trust_and_stale_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = write_package(root)
            store = PluginTrustStore()
            candidate = discover_plugin_packages(root, trust_store=store).candidates[0]
            store.trust(candidate)
            (package / "plugin.py").write_text(PLUGIN_SOURCE + "\n# changed\n", encoding="utf-8")

            changed = discover_plugin_packages(root, trust_store=store).candidates[0]
            self.assertEqual("untrusted", changed.state)
            self.assertNotEqual(candidate.fingerprint, changed.fingerprint)
            with self.assertRaisesRegex(PermissionError, "changed after discovery"):
                load_trusted_plugin_package(candidate, store)

    def test_discovery_isolates_malformed_and_duplicate_packages(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_package(root, "first")
            write_package(root, "second")
            invalid = root / "broken"
            invalid.mkdir()
            (invalid / "plugin.json").write_text("{not json", encoding="utf-8")
            future = write_package(root, "future", plugin_id="com.example.future")
            future_manifest = json.loads((future / "plugin.json").read_text(encoding="utf-8"))
            future_manifest["minimumSdk"] = 999
            (future / "plugin.json").write_text(
                json.dumps(future_manifest), encoding="utf-8"
            )

            report = discover_plugin_packages(root)
            states = {candidate.package_dir.name: candidate.state for candidate in report.candidates}
            self.assertEqual("invalid", states["broken"])
            self.assertEqual("untrusted", states["first"])
            self.assertEqual("invalid", states["future"])
            self.assertEqual("invalid", states["second"])
            duplicate = next(
                candidate for candidate in report.candidates if candidate.package_dir.name == "second"
            )
            self.assertIn("Duplicate discovered plugin ID", duplicate.errors[0])

    def test_repository_example_package_manifest_matches_loaded_plugin(self) -> None:
        examples = Path(__file__).resolve().parents[1] / "examples"
        report = discover_plugin_packages(examples)
        candidate = next(
            item
            for item in report.candidates
            if item.plugin_id == "com.monkez.examples.packaged-notes"
        )
        store = PluginTrustStore()
        store.trust(candidate)
        loaded = load_trusted_plugin_package(candidate, store)
        self.assertEqual(("packaged_note",), loaded.plugin.type_ids)
        self.assertEqual("1.0.0", loaded.plugin.version)
        unload_plugin_package(loaded)


class PluginPackageCanvasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_canvas_requires_exact_trust_and_preserves_records_on_unload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            write_package(project / ".monkez_canva" / "plugins")
            canvas = MonkezCanva()
            canvas.setProjectDirectory(project)
            trust_events = []
            lifecycle = []
            failures = []
            canvas.projectPluginTrustChanged.connect(
                lambda plugin_id, trusted, fingerprint: trust_events.append(
                    (plugin_id, trusted, fingerprint)
                )
            )
            canvas.componentPluginChanged.connect(
                lambda plugin_id, enabled: lifecycle.append((plugin_id, enabled))
            )
            canvas.projectPluginLoadFailed.connect(
                lambda plugin_id, error: failures.append((plugin_id, error))
            )

            record = canvas.projectPlugins()[0]
            self.assertEqual("untrusted", record["state"])
            with self.assertRaisesRegex(PermissionError, "not trusted"):
                canvas.loadProjectPlugin("com.example.packaged")
            self.assertTrue(failures)
            installed = canvas.loadProjectPlugin(
                "com.example.packaged", trust_fingerprint=record["fingerprint"]
            )
            self.assertEqual(("packaged_sensor",), installed)
            self.assertEqual("loaded", canvas.projectPlugins()[0]["state"])
            self.assertEqual("com.example.packaged", trust_events[0][0])
            self.assertTrue(trust_events[0][1])
            self.assertEqual(
                [("com.example.packaged", True)], lifecycle
            )

            element_id = canvas.addElement(
                "packaged_sensor", element_id="temperature"
            )
            original = canvas.element(element_id)
            self.assertEqual(("packaged_sensor",), canvas.unloadProjectPlugin("com.example.packaged"))
            self.assertIs(original, canvas.element(element_id))
            self.assertEqual("__missing__", canvas.element(element_id).definition.plugin_id)
            self.assertEqual("trusted", canvas.projectPlugins()[0]["state"])
            self.assertTrue(canvas.revokeProjectPluginTrust("com.example.packaged"))
            self.assertEqual("untrusted", canvas.projectPlugins()[0]["state"])
            canvas.close()
            canvas.deleteLater()

    def test_plugin_manager_context_and_command_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            write_package(project / ".monkez_canva" / "plugins")
            canvas = MonkezCanva()
            canvas.resize(900, 600)
            canvas.setProjectDirectory(project)
            canvas.setEditMode(True)
            canvas.showProjectPluginManager()
            self.app.processEvents()
            manager = canvas._plugin_manager

            self.assertTrue(manager.isVisible())
            self.assertEqual(1, manager._list.count())
            self.assertEqual("Untrusted", manager._status.text())
            self.assertEqual("Trust and load", manager._action.text())
            labels = {action.text() for action in canvas.createContextMenu().actions()}
            self.assertIn("Project plugins...", labels)
            canvas.showCommandPalette("project plugin manager")
            self.app.processEvents()
            command_ids = {
                str(
                    canvas._command_palette._list.item(index).data(
                        Qt.ItemDataRole.UserRole
                    )
                )
                for index in range(canvas._command_palette._list.count())
            }
            self.assertIn("plugin:manager", command_ids)
            manager._action.click()
            self.app.processEvents()
            self.assertEqual("Loaded", manager._status.text())
            self.assertEqual("Unload", manager._action.text())
            canvas.close()
            canvas.deleteLater()


if __name__ == "__main__":
    unittest.main()
