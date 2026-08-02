from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QSize, pyqtProperty, pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QLineEdit, QSizePolicy, QWidget

from .monkez_button import MonkezButton
from .theme_support import ThemeSupportMixin


DIALOG_MODE_OPTIONS = "0 Open file | 1 Save file | 2 Directory"


class MonkezFilePicker(QWidget, ThemeSupportMixin):
    """Path input plus a themed browse button and validation signals."""

    themeChanged = pyqtSignal(str)
    pathChanged = pyqtSignal(str)
    pathSelected = pyqtSignal(str)
    validityChanged = pyqtSignal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._init_theme_support()
        self._path = ""
        self._dialog_mode = 0
        self._name_filter = "All files (*)"
        self._require_existing = True
        self._button_text = "Browse…"
        self._valid = False
        self._line_edit = QLineEdit(self)
        self._line_edit.setPlaceholderText("Select a file…")
        self._button = MonkezButton(self)
        self._button.setText(self._button_text)
        self._button.setShadowEnabled(False)
        self._button.setFixedWidth(94)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self._line_edit, 1)
        layout.addWidget(self._button)
        self._line_edit.textChanged.connect(self._on_text_changed)
        self._button.clicked.connect(self.browse)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setTheme("material")

    def sizeHint(self) -> QSize:
        return QSize(320, 40)

    def _apply_theme(self) -> None:
        self._button.setTheme(self._theme)
        from .themes import color_to_css, theme_color, theme_radius

        self._line_edit.setStyleSheet(
            "QLineEdit {"
            f"background: {color_to_css(theme_color(self._theme, 'control'))};"
            f"color: {color_to_css(theme_color(self._theme, 'text'))};"
            f"border: 1px solid {color_to_css(theme_color(self._theme, 'border'))};"
            f"border-radius: {theme_radius(self._theme)}px; padding: 8px 10px;"
            "}"
            "QLineEdit:focus {"
            f"border-color: {color_to_css(theme_color(self._theme, 'border_focus'))};"
            "}"
        )

    def _on_text_changed(self, text: str) -> None:
        self._path = text
        valid = bool(text) and (not self._require_existing or Path(text).exists())
        if valid != self._valid:
            self._valid = valid
            self.validityChanged.emit(valid)
        self.pathChanged.emit(text)

    def browse(self) -> None:
        start = self._path or ""
        if self._dialog_mode == 2:
            selected = QFileDialog.getExistingDirectory(self, "Select directory", start)
        elif self._dialog_mode == 1:
            selected, _ = QFileDialog.getSaveFileName(self, "Save file", start, self._name_filter)
        else:
            selected, _ = QFileDialog.getOpenFileName(self, "Open file", start, self._name_filter)
        if selected:
            self.setPath(selected)
            self.pathSelected.emit(selected)

    def clear(self) -> None:
        self.setPath("")

    def getPath(self) -> str:
        return self._path

    def setPath(self, value: str) -> None:
        value = str(value)
        if value == self._line_edit.text():
            return
        self._line_edit.setText(value)

    def getPlaceholderText(self) -> str:
        return self._line_edit.placeholderText()

    def setPlaceholderText(self, value: str) -> None:
        self._line_edit.setPlaceholderText(str(value))

    def getDialogMode(self) -> int:
        return self._dialog_mode

    def setDialogMode(self, value: int) -> None:
        self._dialog_mode = max(0, min(2, int(value)))

    def getDialogModeHint(self) -> str:
        return DIALOG_MODE_OPTIONS

    def setDialogModeHint(self, value: str) -> None:
        return None

    def getNameFilter(self) -> str:
        return self._name_filter

    def setNameFilter(self, value: str) -> None:
        self._name_filter = str(value) or "All files (*)"

    def getRequireExisting(self) -> bool:
        return self._require_existing

    def setRequireExisting(self, value: bool) -> None:
        self._require_existing = bool(value)
        self._on_text_changed(self._path)

    def getButtonText(self) -> str:
        return self._button_text

    def setButtonText(self, value: str) -> None:
        self._button_text = str(value)
        self._button.setText(self._button_text)

    def isValidPath(self) -> bool:
        return self._valid

    path = pyqtProperty(str, getPath, setPath, notify=pathChanged)
    placeholderText = pyqtProperty(str, getPlaceholderText, setPlaceholderText)
    dialogMode = pyqtProperty(int, getDialogMode, setDialogMode)
    dialogModeHint = pyqtProperty(str, getDialogModeHint, setDialogModeHint, stored=False)
    nameFilter = pyqtProperty(str, getNameFilter, setNameFilter)
    requireExisting = pyqtProperty(bool, getRequireExisting, setRequireExisting)
    buttonText = pyqtProperty(str, getButtonText, setButtonText)
    themeIndex = pyqtProperty(int, ThemeSupportMixin.getThemeIndex, ThemeSupportMixin.setThemeIndex)
    themeHint = pyqtProperty(str, ThemeSupportMixin.getThemeOptions, ThemeSupportMixin.setThemeOptions, stored=False)
    themeName = pyqtProperty(str, ThemeSupportMixin.getThemeName, ThemeSupportMixin.setThemeName, designable=False)
