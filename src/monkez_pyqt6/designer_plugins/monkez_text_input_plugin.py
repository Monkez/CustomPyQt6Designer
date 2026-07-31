from __future__ import annotations

from PyQt6.QtDesigner import QPyDesignerCustomWidgetPlugin
from PyQt6.QtGui import QIcon

from monkez_pyqt6.monkez_widgets import MonkezTextInput
from monkez_pyqt6.monkez_widgets.designer_icons import designer_icon

try:
    from plugin_groups import GROUP_INPUTS
except ModuleNotFoundError:
    from .plugin_groups import GROUP_INPUTS

try:
    from _probe import write_probe
except ModuleNotFoundError:
    from ._probe import write_probe

try:
    from theme_task_menu import register_theme_task_menu
except ModuleNotFoundError:
    from .theme_task_menu import register_theme_task_menu


class MonkezTextInputPlugin(QPyDesignerCustomWidgetPlugin):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.initialized = False
        write_probe("MonkezTextInputPlugin.__init__")

    def initialize(self, core) -> None:
        register_theme_task_menu(core, self)
        self.initialized = True

    def isInitialized(self) -> bool:
        return self.initialized

    def createWidget(self, parent):
        write_probe("MonkezTextInputPlugin.createWidget")
        return MonkezTextInput(parent)

    def name(self) -> str:
        return "MonkezTextInput"

    def group(self) -> str:
        return GROUP_INPUTS

    def icon(self) -> QIcon:
        return designer_icon("textinput")

    def toolTip(self) -> str:
        return "Monkez text input"

    def whatsThis(self) -> str:
        return "Text input with configurable radius, colors, icons, padding, and shadow."

    def isContainer(self) -> bool:
        return False

    def includeFile(self) -> str:
        return "monkez_pyqt6.monkez_widgets"

    def domXml(self) -> str:
        return """
<ui language="c++">
 <widget class="MonkezTextInput" name="monkezTextInput">
  <property name="placeholderText">
   <string>Monkez input text...</string>
  </property>
  <property name="themeIndex">
   <number>0</number>
  </property>
 </widget>
</ui>
"""
