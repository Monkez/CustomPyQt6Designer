from __future__ import annotations

from PyQt6.QtDesigner import QPyDesignerCustomWidgetPlugin
from PyQt6.QtGui import QIcon

from monkez_pyqt6.monkez_widgets import MonkezSwitch
from monkez_pyqt6.monkez_widgets.designer_icons import designer_icon

try:
    from plugin_groups import GROUP_ACTIONS
except ModuleNotFoundError:
    from .plugin_groups import GROUP_ACTIONS

try:
    from _probe import write_probe
except ModuleNotFoundError:
    from ._probe import write_probe

try:
    from theme_task_menu import register_theme_task_menu
except ModuleNotFoundError:
    from .theme_task_menu import register_theme_task_menu


class MonkezSwitchPlugin(QPyDesignerCustomWidgetPlugin):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.initialized = False
        write_probe("MonkezSwitchPlugin.__init__")

    def initialize(self, core) -> None:
        register_theme_task_menu(core, self)
        self.initialized = True

    def isInitialized(self) -> bool:
        return self.initialized

    def createWidget(self, parent):
        write_probe("MonkezSwitchPlugin.createWidget")
        return MonkezSwitch(parent)

    def name(self) -> str:
        return "MonkezSwitch"

    def group(self) -> str:
        return GROUP_ACTIONS

    def icon(self) -> QIcon:
        return designer_icon("switch")

    def toolTip(self) -> str:
        return "Themed switch"

    def whatsThis(self) -> str:
        return "Switch/toggle widget with theme and advanced color properties."

    def isContainer(self) -> bool:
        return False

    def includeFile(self) -> str:
        return "monkez_pyqt6.monkez_widgets"

    def domXml(self) -> str:
        return """
<ui language="c++">
 <widget class="MonkezSwitch" name="monkezSwitch">
  <property name="themeIndex">
   <number>1</number>
  </property>
  <property name="checked">
   <bool>false</bool>
  </property>
 </widget>
</ui>
"""
