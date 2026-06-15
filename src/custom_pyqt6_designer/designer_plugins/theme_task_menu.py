from __future__ import annotations

from PyQt6.QtDesigner import QDesignerFormWindowInterface, QExtensionFactory, QPyDesignerTaskMenuExtension
from PyQt6.QtGui import QAction

try:
    from _probe import write_probe
except ModuleNotFoundError:
    from ._probe import write_probe


TASK_MENU_IID = "org.qt-project.Qt.Designer.TaskMenu"
THEME_LABELS = (
    ("Material", "Material", "material", 0),
    ("IOS", "IOS", "ios", 1),
)
THEMED_CLASS_NAMES = {
    "MonkezButton",
    "MonkezCalendarWidget",
    "MonkezCheckBox",
    "MonkezComboBox",
    "MonkezDateEdit",
    "MonkezDateTimeEdit",
    "MonkezDial",
    "MonkezDoubleSpinBox",
    "MonkezFrame",
    "MonkezGroupBox",
    "MonkezLCDNumber",
    "MonkezProgressBar",
    "MonkezRadioButton",
    "MonkezScrollArea",
    "MonkezSlider",
    "MonkezSpinBox",
    "MonkezTextInput",
    "MonkezTimeEdit",
    "MonkezSwitch",
}


class MonkezThemeTaskMenu(QPyDesignerTaskMenuExtension):
    def __init__(self, widget, parent=None) -> None:
        super().__init__(parent)
        self._widget = widget
        self._actions = []

        for label, enum_key, theme_name, theme_index in THEME_LABELS:
            action = QAction(f"Monkez Theme: {label}", self)
            action.triggered.connect(
                lambda checked=False, key=enum_key, name=theme_name, index=theme_index: self._apply_theme(
                    key, name, index
                )
            )
            self._actions.append(action)

    def preferredEditAction(self):
        return self._actions[0] if self._actions else None

    def taskActions(self):
        return self._actions

    def _apply_theme(self, enum_key: str, theme_name: str, theme_index: int) -> None:
        class_name = type(self._widget).__name__
        scoped_value = f"{class_name}::{enum_key}"
        write_probe(f"{class_name}.taskMenuTheme={scoped_value}/{theme_name}")

        if hasattr(self._widget, "setThemeIndex"):
            self._widget.setThemeIndex(theme_index)
        elif hasattr(self._widget, "setThemePreset"):
            self._widget.setThemePreset(enum_key)

        form = QDesignerFormWindowInterface.findFormWindow(self._widget)
        if form is None:
            return

        cursor = form.cursor()
        if cursor is not None:
            cursor.setWidgetProperty(self._widget, "themeIndex", theme_index)
        form.setDirty(True)


class MonkezThemeTaskMenuFactory(QExtensionFactory):
    def createExtension(self, object, iid: str, parent):
        if iid != TASK_MENU_IID:
            return None
        if type(object).__name__ not in THEMED_CLASS_NAMES:
            return None
        write_probe(f"MonkezThemeTaskMenuFactory.createExtension:{type(object).__name__}")
        return MonkezThemeTaskMenu(object, parent)


def register_theme_task_menu(core, plugin) -> None:
    manager = core.extensionManager()
    if manager is None:
        return
    if getattr(plugin, "_theme_task_menu_registered", False):
        return
    plugin._theme_task_menu_factory = MonkezThemeTaskMenuFactory(manager)
    manager.registerExtensions(plugin._theme_task_menu_factory, TASK_MENU_IID)
    plugin._theme_task_menu_registered = True
