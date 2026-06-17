from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from custom_pyqt6_designer.gallery_app import GalleryWindow, WIDGET_DOCS
from custom_pyqt6_designer.monkez_widgets import __all__ as MONKEZ_WIDGETS


class GalleryAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_docs_cover_public_widgets(self) -> None:
        documented = {doc.name for doc in WIDGET_DOCS}
        missing = sorted(set(MONKEZ_WIDGETS) - documented)
        self.assertEqual([], missing)

    def test_gallery_window_can_be_created(self) -> None:
        window = GalleryWindow()
        try:
            tabs = window.centralWidget()
            self.assertEqual(5, tabs.count())
            self.assertGreater(window._docs_list.count(), 0)
        finally:
            window.close()
            window.deleteLater()


if __name__ == "__main__":
    unittest.main()
