from custom_pyqt6_designer.monkez_widgets import MonkezDateTimeEdit

try:
    from plugin_factory import PluginSpec, create_plugin
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin


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
    ),
    __name__,
)
