from custom_pyqt6_designer.monkez_widgets import MonkezCalendarWidget

try:
    from plugin_factory import PluginSpec, create_plugin
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin


MonkezCalendarWidgetPlugin = create_plugin(
    PluginSpec(
        MonkezCalendarWidget,
        "MonkezCalendarWidget",
        "monkezCalendarWidget",
        "calendar",
        "Themed calendar",
        "Calendar with styled navigation, selection, grid, date limits, and configurable colors.",
        320,
        240,
    ),
    __name__,
)
