from __future__ import annotations

from PyQt6.QtDesigner import QExtensionFactory, QPyDesignerContainerExtension

from custom_pyqt6_designer.monkez_widgets import MonkezScrollArea

try:
    from _probe import write_probe
except ModuleNotFoundError:
    from ._probe import write_probe


CONTAINER_IID = "org.qt-project.Qt.Designer.Container"


class MonkezScrollAreaContainerExtension(QPyDesignerContainerExtension):
    """Expose the scroll area's fixed content widget to Qt Designer."""

    def __init__(self, scroll_area: MonkezScrollArea, parent=None) -> None:
        super().__init__(parent)
        self._scroll_area = scroll_area

    def count(self) -> int:
        return 1 if self._scroll_area.widget() is not None else 0

    def widget(self, index: int):
        if index != 0:
            return None
        return self._scroll_area.widget()

    def currentIndex(self) -> int:
        return 0 if self.count() else -1

    def setCurrentIndex(self, index: int) -> None:
        return None

    def canAddWidget(self) -> bool:
        return False

    def canRemove(self, index: int) -> bool:
        return False

    def addWidget(self, widget) -> None:
        if self._scroll_area.widget() is None:
            self._scroll_area.setWidget(widget)

    def insertWidget(self, index: int, widget) -> None:
        self.addWidget(widget)

    def remove(self, index: int) -> None:
        return None


class MonkezScrollAreaContainerFactory(QExtensionFactory):
    def createExtension(self, object, iid: str, parent):
        if iid != CONTAINER_IID or not isinstance(object, MonkezScrollArea):
            return None
        write_probe("MonkezScrollAreaContainerFactory.createExtension")
        return MonkezScrollAreaContainerExtension(object, parent)


def register_scroll_area_container(core, plugin) -> None:
    manager = core.extensionManager()
    if manager is None:
        return
    if getattr(plugin, "_scroll_area_container_registered", False):
        return
    plugin._scroll_area_container_factory = MonkezScrollAreaContainerFactory(manager)
    manager.registerExtensions(plugin._scroll_area_container_factory, CONTAINER_IID)
    plugin._scroll_area_container_registered = True
