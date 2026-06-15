from custom_pyqt6_designer.monkez_widgets import MonkezDateTimeEdit

try:
    from plugin_factory import PluginSpec, create_plugin
    from plugin_groups import GROUP_VALUES
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin
    from .plugin_groups import GROUP_VALUES


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
        group=GROUP_VALUES,
    ),
    __name__,
)
