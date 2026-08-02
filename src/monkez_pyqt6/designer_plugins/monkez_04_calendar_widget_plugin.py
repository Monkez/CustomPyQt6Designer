from monkez_pyqt6.monkez_widgets import MonkezCalendarWidget

try:
    from plugin_factory import PluginSpec, create_plugin
    from plugin_groups import GROUP_DATETIME
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin
    from .plugin_groups import GROUP_DATETIME


MonkezCalendarWidgetPlugin = create_plugin(
    PluginSpec(
        MonkezCalendarWidget,
        "MonkezCalendarWidget",
        "monkezCalendarWidget",
        "calendar",
        "Themed calendar",
        "Calendar with styled navigation, selection, grid, date limits, and configurable colors.",
        380,
        320,
        group=GROUP_DATETIME,
    ),
    __name__,
)
