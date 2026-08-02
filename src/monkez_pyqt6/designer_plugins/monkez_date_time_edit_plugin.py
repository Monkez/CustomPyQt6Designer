from monkez_pyqt6.monkez_widgets import MonkezDateTimeEdit

try:
    from plugin_factory import PluginSpec, create_plugin
    from plugin_groups import GROUP_DATETIME
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin
    from .plugin_groups import GROUP_DATETIME


MonkezDateTimeEditPlugin = create_plugin(
    PluginSpec(
        MonkezDateTimeEdit,
        "MonkezDateTimeEdit",
        "monkezDateTimeEdit",
        "datetimeedit",
        "Themed date and time editor",
        "Date-time editor with calendar popup and configurable theme, colors, radius, and format.",
        220,
        40,
        group=GROUP_DATETIME,
    ),
    __name__,
)
