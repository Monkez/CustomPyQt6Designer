from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtDesigner import QPyDesignerCustomWidgetPlugin

from custom_pyqt6_designer.monkez_widgets.designer_icons import designer_icon

try:
    from _probe import write_probe
except ModuleNotFoundError:
    from ._probe import write_probe

try:
    from theme_task_menu import register_theme_task_menu
except ModuleNotFoundError:
    from .theme_task_menu import register_theme_task_menu


@dataclass(frozen=True)
class PluginSpec:
    widget_type: type
    class_name: str
    object_name: str
    icon_name: str
    tooltip: str
    whats_this: str
    width: int = 180
    height: int = 40
    container: bool = False
    themed: bool = True
    properties_xml: str = ""
    group: str = "Monkez Widgets"


def create_plugin(spec: PluginSpec, module_name: str):
    def __init__(self, parent=None) -> None:
        QPyDesignerCustomWidgetPlugin.__init__(self, parent)
        self._initialized = False
        write_probe(f"{spec.class_name}Plugin.__init__")

    def initialize(self, core) -> None:
        if self._initialized:
            return
        if spec.themed:
            register_theme_task_menu(core, self)
        self._initialized = True

    def is_initialized(self) -> bool:
        return self._initialized

    def create_widget(self, parent):
        write_probe(f"{spec.class_name}Plugin.createWidget")
        return spec.widget_type(parent)

    def name(self) -> str:
        return spec.class_name

    def group(self) -> str:
        return spec.group

    def icon(self):
        return designer_icon(spec.icon_name)

    def tool_tip(self) -> str:
        return spec.tooltip

    def whats_this(self) -> str:
        return spec.whats_this

    def is_container(self) -> bool:
        return spec.container

    def include_file(self) -> str:
        return "custom_pyqt6_designer.monkez_widgets"

    def dom_xml(self) -> str:
        properties = spec.properties_xml.strip()
        if properties:
            properties = f"\n{properties}"
        return (
            '<ui language="c++">\n'
            f' <widget class="{spec.class_name}" name="{spec.object_name}">\n'
            "  <property name=\"geometry\">\n"
            "   <rect>\n"
            "    <x>0</x><y>0</y>"
            f"<width>{spec.width}</width><height>{spec.height}</height>\n"
            "   </rect>\n"
            f"  </property>{properties}\n"
            " </widget>\n"
            "</ui>\n"
        )

    attributes = {
        "__module__": module_name,
        "__init__": __init__,
        "initialize": initialize,
        "isInitialized": is_initialized,
        "createWidget": create_widget,
        "name": name,
        "group": group,
        "icon": icon,
        "toolTip": tool_tip,
        "whatsThis": whats_this,
        "isContainer": is_container,
        "includeFile": include_file,
        "domXml": dom_xml,
    }
    return type(f"{spec.class_name}Plugin", (QPyDesignerCustomWidgetPlugin,), attributes)
