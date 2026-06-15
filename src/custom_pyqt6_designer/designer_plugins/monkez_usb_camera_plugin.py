from __future__ import annotations

from PyQt6.QtDesigner import QPyDesignerCustomWidgetPlugin
from PyQt6.QtGui import QIcon

from custom_pyqt6_designer.monkez_widgets import MonkezUSBCamera
from custom_pyqt6_designer.monkez_widgets.designer_icons import designer_icon

try:
    from plugin_groups import GROUP_MEDIA
except ModuleNotFoundError:
    from .plugin_groups import GROUP_MEDIA

try:
    from _probe import write_probe
except ModuleNotFoundError:
    from ._probe import write_probe


class MonkezUSBCameraPlugin(QPyDesignerCustomWidgetPlugin):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.initialized = False
        write_probe("MonkezUSBCameraPlugin.__init__")

    def initialize(self, core) -> None:
        self.initialized = True

    def isInitialized(self) -> bool:
        return self.initialized

    def createWidget(self, parent):
        write_probe("MonkezUSBCameraPlugin.createWidget")
        return MonkezUSBCamera(parent)

    def name(self) -> str:
        return "MonkezUSBCamera"

    def group(self) -> str:
        return GROUP_MEDIA

    def icon(self) -> QIcon:
        return designer_icon("camera")

    def toolTip(self) -> str:
        return "Monkez USB camera"

    def whatsThis(self) -> str:
        return "Design-time safe USB camera widget with backend, source, resolution, FPS, and reconnect options."

    def isContainer(self) -> bool:
        return False

    def includeFile(self) -> str:
        return "custom_pyqt6_designer.monkez_widgets"

    def domXml(self) -> str:
        return """
<ui language="c++">
 <widget class="MonkezUSBCamera" name="monkezUSBCamera">
  <property name="backend">
   <string>auto</string>
  </property>
  <property name="cameraSource">
   <string>0</string>
  </property>
  <property name="cameraIndex">
   <number>0</number>
  </property>
  <property name="resolutionWidth">
   <number>1280</number>
  </property>
  <property name="resolutionHeight">
   <number>720</number>
  </property>
  <property name="fps">
   <number>30</number>
  </property>
  <property name="displayFps">
   <number>30</number>
  </property>
  <property name="fourcc">
   <string>MJPG</string>
  </property>
  <property name="bufferSize">
   <number>1</number>
  </property>
  <property name="mirror">
   <bool>false</bool>
  </property>
  <property name="autoStart">
   <bool>false</bool>
  </property>
  <property name="previewAutoStart">
   <bool>true</bool>
  </property>
  <property name="reconnect">
   <bool>true</bool>
  </property>
  <property name="reconnectIntervalMs">
   <number>1000</number>
  </property>
 </widget>
</ui>
"""
