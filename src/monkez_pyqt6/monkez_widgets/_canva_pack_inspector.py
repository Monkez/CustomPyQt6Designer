"""Compact schema-driven Inspector used by the built-in component packs."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)


_HIDDEN_PROPERTIES = {
    "packVisual",
    "ports",
    "bindings",
    "data",
    "text",
    "color",
    "background",
    "textColor",
    "metadata",
    "opacity",
    "rotation",
    "z",
    "x",
    "y",
    "width",
    "height",
    "locked",
    "hidden",
}


class _PackInspector(QWidget):
    def __init__(self, canvas, item) -> None:
        super().__init__()
        self._canvas = canvas
        self._element_id = item.element_id
        self._fields: dict[str, tuple[QWidget, Mapping[str, Any]]] = {}
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._apply)
        self.setObjectName("CanvasPackInspector")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        heading = QFrame()
        heading.setObjectName("CanvasPackInspectorHeading")
        heading_layout = QVBoxLayout(heading)
        heading_layout.setContentsMargins(12, 9, 12, 9)
        heading_layout.setSpacing(1)
        title = QLabel("Component properties")
        title.setObjectName("CanvasPackInspectorTitle")
        subtitle = QLabel(item.definition.label if item.definition is not None else item.kind)
        subtitle.setObjectName("CanvasPackInspectorSubtitle")
        heading_layout.addWidget(title)
        heading_layout.addWidget(subtitle)
        layout.addWidget(heading)

        form_host = QFrame()
        form_host.setObjectName("CanvasPackInspectorForm")
        form = QFormLayout(form_host)
        form.setContentsMargins(12, 10, 12, 11)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        definition = item.definition
        properties = {} if definition is None else definition.schema.get("properties", {})
        record = canvas.documentModel().element(item.element_id).to_dict()
        for name, raw_rule in properties.items():
            if name in _HIDDEN_PROPERTIES or not isinstance(raw_rule, Mapping):
                continue
            rule = dict(raw_rule)
            label = QLabel(str(rule.get("title", name.replace("_", " ").title())))
            label.setObjectName("CanvasPackInspectorLabel")
            field = self._make_field(name, rule, record.get(name))
            form.addRow(label, field)
            self._fields[name] = (field, rule)
        layout.addWidget(form_host)
        if not self._fields:
            form.addRow(QLabel("No component-specific properties"))

        self.setStyleSheet("""
            #CanvasPackInspectorHeading, #CanvasPackInspectorForm {
                background: #fffdfb;
                border: 1px solid #e8e3de;
                border-radius: 10px;
            }
            #CanvasPackInspectorTitle {
                color: #27303d;
                font-size: 12px;
                font-weight: 650;
                border: none;
                background: transparent;
            }
            #CanvasPackInspectorSubtitle, #CanvasPackInspectorLabel {
                color: #788395;
                font-size: 10px;
                border: none;
                background: transparent;
            }
            #CanvasPackInspectorForm QLineEdit,
            #CanvasPackInspectorForm QComboBox,
            #CanvasPackInspectorForm QPlainTextEdit {
                min-height: 28px;
                color: #27303d;
                background: #ffffff;
                border: 1px solid #ddd8d2;
                border-radius: 7px;
                padding: 2px 8px;
                selection-background-color: #ff786d;
            }
            #CanvasPackInspectorForm QLineEdit:focus,
            #CanvasPackInspectorForm QComboBox:focus,
            #CanvasPackInspectorForm QPlainTextEdit:focus {
                border-color: #ff786d;
            }
            #CanvasPackInspectorForm QCheckBox {
                color: #3f4856;
                spacing: 7px;
            }
        """)

    def _make_field(self, name: str, rule: Mapping[str, Any], value: Any) -> QWidget:
        expected = str(rule.get("type", "string"))
        choices = rule.get("enum")
        if isinstance(choices, (list, tuple)):
            field = QComboBox()
            field.addItems(str(choice) for choice in choices)
            field.setCurrentText(str(value))
            field.currentTextChanged.connect(self._schedule)
            return field
        if expected == "boolean":
            field = QCheckBox("Enabled")
            field.setChecked(bool(value))
            field.toggled.connect(self._schedule)
            return field
        if expected in ("array", "object"):
            field = QPlainTextEdit()
            field.setObjectName(f"pack_{name}")
            field.setFixedHeight(58)
            field.setPlainText(
                json.dumps(value if value is not None else ([] if expected == "array" else {}), ensure_ascii=False)
            )
            field.textChanged.connect(self._schedule)
            return field
        field = QLineEdit("" if value is None else str(value))
        field.setObjectName(f"pack_{name}")
        if expected in ("number", "integer"):
            minimum = rule.get("minimum")
            maximum = rule.get("maximum")
            limits = []
            if minimum is not None:
                limits.append(f"min {minimum:g}")
            if maximum is not None:
                limits.append(f"max {maximum:g}")
            field.setPlaceholderText(" · ".join(limits))
        field.editingFinished.connect(self._schedule)
        return field

    def _schedule(self, *_args) -> None:
        self._timer.start(0)

    @staticmethod
    def _field_value(field: QWidget, rule: Mapping[str, Any]) -> Any:
        expected = str(rule.get("type", "string"))
        if isinstance(field, QCheckBox):
            return field.isChecked()
        if isinstance(field, QComboBox):
            return field.currentText()
        if isinstance(field, QPlainTextEdit):
            value = json.loads(field.toPlainText() or ("[]" if expected == "array" else "{}"))
            if expected == "array" and not isinstance(value, list):
                raise TypeError("Expected a JSON array")
            if expected == "object" and not isinstance(value, dict):
                raise TypeError("Expected a JSON object")
            return value
        text = field.text() if isinstance(field, QLineEdit) else ""
        if expected == "number":
            return float(text)
        if expected == "integer":
            value = float(text)
            if not value.is_integer():
                raise ValueError("Expected a whole number")
            return int(value)
        return text

    def _apply(self) -> None:
        try:
            values = {name: self._field_value(field, rule) for name, (field, rule) in self._fields.items()}
            self._canvas.updateElement(self._element_id, **values)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            self._canvas.diagnosticMessage.emit(f"Component property change rejected for {self._element_id}: {error}")


def create_component_pack_inspector(canvas, item) -> QWidget:
    return _PackInspector(canvas, item)


__all__ = ["create_component_pack_inspector"]
