from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from custom_pyqt6_designer.splash_template import (
    bundled_splash_template,
    create_splash_ui,
)


class SplashTemplateTests(unittest.TestCase):
    def test_bundled_template_is_a_standalone_splash_form(self) -> None:
        content = bundled_splash_template().read_text(encoding="utf-8")

        self.assertIn('<widget class="MonkezSplashScreen" name="AppSplash">', content)
        self.assertIn('<container>1</container>', content)

    def test_create_splash_ui_copies_template(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "ui" / "startup.ui"

            result, created = create_splash_ui(destination)

            self.assertTrue(created)
            self.assertEqual(result, destination.resolve())
            self.assertEqual(
                result.read_bytes(),
                bundled_splash_template().read_bytes(),
            )

    def test_existing_splash_form_is_opened_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "startup.ui"
            destination.write_text("user design", encoding="utf-8")

            result, created = create_splash_ui(destination)

            self.assertFalse(created)
            self.assertEqual(result.read_text(encoding="utf-8"), "user design")


if __name__ == "__main__":
    unittest.main()
