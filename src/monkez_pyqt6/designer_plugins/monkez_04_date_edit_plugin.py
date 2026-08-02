from monkez_pyqt6.monkez_widgets import MonkezDateEdit

try:
    from plugin_factory import PluginSpec, create_plugin
    from plugin_groups import GROUP_DATETIME
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin
    from .plugin_groups import GROUP_DATETIME


MonkezDateEditPlugin = create_plugin(
    PluginSpec(
        MonkezDateEdit,
        "MonkezDateEdit",
        "monkezDateEdit",
        "dateedit",
        "Themed date editor",
        "Date editor with calendar popup and configurable theme, colors, radius, and display format.",
        group=GROUP_DATETIME,
    ),
    __name__,
)
