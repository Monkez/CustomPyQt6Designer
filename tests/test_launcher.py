from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import custom_pyqt6_designer.launcher as launcher
from custom_pyqt6_designer.launcher import (
    ENV_APP_ICON,
    append_path,
    app_icon_path,
    build_env,
    configure_frozen_python_runtime,
    package_root,
)


class LauncherTests(unittest.TestCase):
    def test_source_logo_is_exposed_to_designer_process(self) -> None:
        icon_path = app_icon_path()

        self.assertIsNotNone(icon_path)
        self.assertEqual(Path(build_env()[ENV_APP_ICON]), icon_path)

    def test_append_path_moves_existing_entry_to_front(self) -> None:
        separator = os.pathsep
        value = separator.join(["stale", "source", "other"])

        result = append_path(value, "source", separator)

        self.assertEqual(result.split(separator), ["source", "stale", "other"])

    def test_source_root_is_first_pythonpath_entry(self) -> None:
        import_root = str(package_root().parent)

        entries = build_env()["PYTHONPATH"].split(os.pathsep)

        self.assertEqual(entries[0], import_root)
        self.assertEqual(entries.count(import_root), 1)

    def test_frozen_runtime_sets_pythonhome_and_standard_library_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            internal_dir = Path(temp_dir)
            runtime_dir = internal_dir / "python_runtime"
            (runtime_dir / "Lib").mkdir(parents=True)
            (runtime_dir / "DLLs").mkdir()
            (runtime_dir / "Lib" / "pkgutil.py").touch()
            (runtime_dir / "python311.dll").touch()
            env = {"PATH": "system", "PYTHONPATH": ""}

            configured = configure_frozen_python_runtime(env, internal_dir, os.pathsep)

            self.assertTrue(configured)
            self.assertEqual(env["PYTHONHOME"], str(runtime_dir))
            self.assertEqual(env["PYTHONPATH"].split(os.pathsep)[0], str(internal_dir))
            self.assertIn(str(runtime_dir / "Lib"), env["PYTHONPATH"].split(os.pathsep))
            self.assertIn(str(runtime_dir / "DLLs"), env["PATH"].split(os.pathsep))

    def test_plugin_verifier_rejects_designer_that_exits_early(self) -> None:
        class ExitingProcess:
            def __init__(self, *args, **kwargs) -> None:
                self.returncode = 1

            def poll(self):
                return self.returncode

        with patch.object(launcher.subprocess, "Popen", ExitingProcess):
            result = launcher.verify_designer_plugins(["designer"], {}, expected_plugins=1)

        self.assertEqual(result, 1)


if __name__ == "__main__":
    unittest.main()
