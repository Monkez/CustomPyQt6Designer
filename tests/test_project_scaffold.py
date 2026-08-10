import tempfile
import unittest
from pathlib import Path

from monkez_pyqt6.project import create_project


class ProjectScaffoldTests(unittest.TestCase):
    def test_create_project_generates_portable_structure(self):
        with tempfile.TemporaryDirectory() as temp:
            root = create_project(Path(temp) / "demo", name="demo", run_setup=False)
            self.assertTrue((root / "main.py").is_file())
            self.assertTrue((root / "assets" / "qt-uis" / "main.ui").is_file())
            self.assertTrue((root / "assets" / "configs" / "config.json").is_file())
            self.assertTrue((root / "requirements.txt").is_file())
            setup_text = (root / "setup.bat").read_text(encoding="utf-8")
            self.assertIn(".venv", setup_text)
            self.assertIn("uv venv", setup_text)
            self.assertIn("git+https://github.com/Monkez/CustomPyQt6Designer.git@main", (root / "requirements.txt").read_text(encoding="utf-8"))
            for script in ("setup.bat", "run.bat", "build.bat"):
                self.assertTrue((root / script).is_file())

    def test_rejects_non_empty_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "demo"
            root.mkdir()
            (root / "existing.txt").write_text("owned", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                create_project(root, name="demo")

