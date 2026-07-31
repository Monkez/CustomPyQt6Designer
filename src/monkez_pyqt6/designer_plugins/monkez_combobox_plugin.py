from __future__ import annotations

from PyQt6.QtDesigner import QPyDesignerCustomWidgetPlugin
from PyQt6.QtGui import QIcon

from monkez_pyqt6.monkez_widgets import MonkezComboBox
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


class MonkezComboBoxPlugin(QPyDesignerCustomWidgetPlugin):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.initialized = False
        write_probe("MonkezComboBoxPlugin.__init__")

    def initialize(self, core) -> None:
        register_theme_task_menu(core, self)
        self.initialized = True

    def isInitialized(self) -> bool:
        return self.initialized

    def createWidget(self, parent):
        write_probe("MonkezComboBoxPlugin.createWidget")
        return MonkezComboBox(parent)

    def name(self) -> str:
        return "MonkezComboBox"

    def group(self) -> str:
        return GROUP_INPUTS

    def icon(self) -> QIcon:
        return designer_icon("combobox")

    def toolTip(self) -> str:
        return "Monkez combo box"

    def whatsThis(self) -> str:
        return "Custom combo box with configurable color properties."

    def isContainer(self) -> bool:
        return False

    def includeFile(self) -> str:
        return "monkez_pyqt6.monkez_widgets"

    def domXml(self) -> str:
        return """
<ui language="c++">
 <widget class="MonkezComboBox" name="monkezComboBox">
  <property name="themeIndex">
   <number>0</number>
  </property>
 </widget>
</ui>
"""
