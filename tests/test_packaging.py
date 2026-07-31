from __future__ import annotations

import importlib.util
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def test_distribution_and_import_package_use_the_new_name(self) -> None:
        metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(metadata["project"]["name"], "monkez-pyqt6")
        self.assertTrue((ROOT / "src" / "monkez_pyqt6").is_dir())

    def test_legacy_import_and_launcher_shims_are_packaged(self) -> None:
        compatibility_package = ROOT / "src" / "custom_pyqt6_designer"
        self.assertTrue((compatibility_package / "__init__.py").is_file())
        self.assertTrue((compatibility_package / "__main__.py").is_file())

    def test_package_versions_are_synchronized(self) -> None:
        metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        package_init = ROOT / "src" / "monkez_pyqt6" / "__init__.py"
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
            "install_designer.bat",
            "new_splash.bat",
            "uninstall_designer.bat",
        }
        self.assertEqual(
            {path.name for path in ROOT.glob("*.bat")} & expected,
            expected,
        )

    def test_portable_release_contains_onboarding_files(self) -> None:
        portable_files = ROOT / "packaging" / "portable"
        self.assertTrue((portable_files / "START_HERE.txt").is_file())
        self.assertTrue((portable_files / "Open Monkez Designer.bat").is_file())
        self.assertTrue((portable_files / "New Splash Screen.bat").is_file())

    def test_standalone_splash_template_is_packaged(self) -> None:
        self.assertTrue(
            (
                ROOT
                / "src"
                / "monkez_pyqt6"
                / "templates"
                / "monkez_splash_screen.ui"
            ).is_file()
        )

    def test_module_launcher_is_packaged(self) -> None:
        self.assertTrue(
            (ROOT / "src" / "monkez_pyqt6" / "__main__.py").is_file()
        )


if __name__ == "__main__":
    unittest.main()
