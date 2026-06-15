from __future__ import annotations

from PyQt6.QtDesigner import QPyDesignerCustomWidgetPlugin
from PyQt6.QtGui import QIcon

from custom_pyqt6_designer.monkez_widgets import MonkezRadioButton
from custom_pyqt6_designer.monkez_widgets.designer_icons import designer_icon

try:
    from _probe import write_probe
except ModuleNotFoundError:
    from ._probe import write_probe

try:
    from theme_task_menu import register_theme_task_menu
except ModuleNotFoundError:
    from .theme_task_menu import register_theme_task_menu


class MonkezRadioButtonPlugin(QPyDesignerCustomWidgetPlugin):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.initialized = False
        write_probe("MonkezRadioButtonPlugin.__init__")

    def initialize(self, core) -> None:
        register_theme_task_menu(core, self)
        self.initialized = True

    def isInitialized(self) -> bool:
        return self.initialized

    def createWidget(self, parent):
        write_probe("MonkezRadioButtonPlugin.createWidget")
        return MonkezRadioButton(parent)

    def name(self) -> str:
        return "MonkezRadioButton"

    def group(self) -> str:
        return "Monkez Widgets"

    def icon(self) -> QIcon:
        return designer_icon("radio")

    def toolTip(self) -> str:
        return "Themed radio button"

    def whatsThis(self) -> str:
        return "Radio button with theme preset and advanced indicator color properties."

    def isContainer(self) -> bool:
        return False

    def includeFile(self) -> str:
        return "custom_pyqt6_designer.monkez_widgets"

    def domXml(self) -> str:
        return """
<ui language="c++">
 <widget class="MonkezRadioButton" name="monkezRadioButton">
  <property name="text">
   <string>Monkez Radio</string>
  </property>
  <property name="themeIndex">
   <number>0</number>
  </property>
 </widget>
</ui>
"""
