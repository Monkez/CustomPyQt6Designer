from __future__ import annotations

from PyQt6.QtDesigner import QPyDesignerCustomWidgetPlugin
from PyQt6.QtGui import QIcon

from custom_pyqt6_designer.monkez_widgets import MonkezImage
from custom_pyqt6_designer.monkez_widgets.designer_icons import designer_icon

try:
    from _probe import write_probe
except ModuleNotFoundError:
    from ._probe import write_probe


class MonkezImagePlugin(QPyDesignerCustomWidgetPlugin):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.initialized = False
        write_probe("MonkezImagePlugin.__init__")

    def initialize(self, core) -> None:
        self.initialized = True

    def isInitialized(self) -> bool:
        return self.initialized

    def createWidget(self, parent):
        write_probe("MonkezImagePlugin.createWidget")
        return MonkezImage(parent)

    def name(self) -> str:
        return "MonkezImage"

    def group(self) -> str:
        return "Monkez Widgets"

    def icon(self) -> QIcon:
        return designer_icon("image")

    def toolTip(self) -> str:
        return "Monkez image"

    def whatsThis(self) -> str:
        return "Image display widget with configurable background color and image file."

    def isContainer(self) -> bool:
        return False

    def includeFile(self) -> str:
        return "custom_pyqt6_designer.monkez_widgets"

    def domXml(self) -> str:
        return """
<ui language="c++">
 <widget class="MonkezImage" name="monkezImage"/>
</ui>
"""
