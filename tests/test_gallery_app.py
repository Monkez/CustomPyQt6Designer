from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWidgets import QApplication

from custom_pyqt6_designer.gallery_app import (
    FLUENT_METHOD_PROBES,
    WIDGET_METHOD_PROBES,
    GalleryWindow,
    WIDGET_DOCS,
    _create_doc_preview_widget,
    _supported_fluent_method_docs,
)
from custom_pyqt6_designer.monkez_widgets import MonkezButton, MonkezRadioButton
from custom_pyqt6_designer.monkez_widgets import __all__ as MONKEZ_WIDGETS


class GalleryAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_docs_cover_public_widgets(self) -> None:
        documented = {doc.name for doc in WIDGET_DOCS}
        missing = sorted(set(MONKEZ_WIDGETS) - documented)
        self.assertEqual([], missing)

    def test_supported_fluent_docs_match_runtime_methods(self) -> None:
        probes = {label: probe for label, _description, _command, probe in FLUENT_METHOD_PROBES}
        for doc in WIDGET_DOCS:
            with self.subTest(widget=doc.name):
                probes.update({label: probe for label, _description, _command, probe in WIDGET_METHOD_PROBES.get(doc.name, ())})
                rows = _supported_fluent_method_docs(doc.name)
                self.assertGreater(len(rows), 0)
                row_labels = {label for label, _description, _command in rows}
                expected_labels = {label for label, _description, _command, _probe in WIDGET_METHOD_PROBES.get(doc.name, ())}
                self.assertTrue(expected_labels <= row_labels)
                for label, _description, command in rows:
                    self.assertTrue(command)
                    widget = _create_doc_preview_widget(doc.name)
                    try:
                        probes[label](widget)
                    finally:
                        widget.deleteLater()

    def test_gallery_window_can_be_created(self) -> None:
        window = GalleryWindow()
        try:
            self.assertEqual("Monkez Widget Docs Lab", window.windowTitle())
            self.assertFalse(hasattr(window, "_tabs"))
            self.assertGreater(window._docs_list.count(), 0)
            docs_html = window._docs_browser.toHtml()
            self.assertIn("Supported runtime methods", docs_html)
            self.assertIn("setThemeIndex(index)", docs_html)
            self.assertIn("setButtonTypeIndex(index)", docs_html)
            self.assertIn("setBackground(color)", docs_html)
            self.assertIn("setColors(**roles)", docs_html)
            self.assertIn("method:setBackground%28color%29", docs_html)
            self.assertIn("method:setButtonTypeIndex%28index%29", docs_html)
            self.assertNotIn("Theme indexes", docs_html)
            self.assertNotIn("Properties", docs_html)
            self.assertNotIn("Methods / Signals", docs_html)
            self.assertIsInstance(window._docs_preview_widget, MonkezButton)
            window._handle_doc_link(QUrl("method:setButtonTypeIndex%28index%29"))
            self.assertEqual("setButtonTypeIndex(1)", window._docs_method_input.text())
            window._handle_doc_link(QUrl("method:setBackground%28color%29"))
            self.assertEqual('setBackground("#2563eb")', window._docs_method_input.text())
            window._set_selected_color("#ef4444")
            self.assertEqual('setBackground("#2563eb")', window._docs_method_input.text())
            self.assertEqual("#ef4444", QApplication.clipboard().text())
            window._color_format_combo.setCurrentText("RGB tuple")
            self.assertEqual("(239, 68, 68)", QApplication.clipboard().text())
            window._color_format_combo.setCurrentText("QColor")
            self.assertEqual('QColor("#ef4444")', QApplication.clipboard().text())
            window._docs_method_input.setText('widget.setBackground("#123456")')
            window._run_doc_method()
            self.assertEqual("#123456", window._docs_preview_widget.activeColor.name())
            window._docs_method_input.setText('setColor("#2563eb")')
            window._run_doc_method()
            self.assertEqual("#2563eb", window._docs_preview_widget.activeColor.name())
            window._reset_doc_preview()
            self.assertIsInstance(window._docs_preview_widget, MonkezButton)
            self.assertNotEqual("#2563eb", window._docs_preview_widget.activeColor.name())

            radio_items = window._docs_list.findItems("MonkezRadioButton", Qt.MatchFlag.MatchExactly)
            self.assertEqual(1, len(radio_items))
            window._docs_list.setCurrentItem(radio_items[0])
            self.assertIsInstance(window._docs_preview_widget, MonkezRadioButton)
            window._docs_method_input.setText("setBackground('#2563eb')")
            window._run_doc_method()
            self.assertEqual("#2563eb", window._docs_preview_widget.backgroundColor.name())
            self.assertNotIn("Error:", window._docs_method_status.text())
        finally:
            window.close()
            window.deleteLater()


if __name__ == "__main__":
    unittest.main()
