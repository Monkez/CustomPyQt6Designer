from __future__ import annotations

import importlib.util
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def test_package_versions_are_synchronized(self) -> None:
        metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        package_init = ROOT / "src" / "custom_pyqt6_designer" / "__init__.py"
        spec = importlib.util.spec_from_file_location("package_version_probe", package_init)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        self.assertEqual(metadata["project"]["version"], module.__version__)

    def test_windows_helper_scripts_are_available(self) -> None:
        expected = {
            "setup.bat",
            "run.bat",
            "gallery.bat",
            "demo.bat",
            "test.bat",
            "build.bat",
            "build_splash_demo.bat",
            "run_splash_exe_demo.bat",
        }
        self.assertEqual(
            {path.name for path in ROOT.glob("*.bat")} & expected,
            expected,
        )


if __name__ == "__main__":
    unittest.main()
