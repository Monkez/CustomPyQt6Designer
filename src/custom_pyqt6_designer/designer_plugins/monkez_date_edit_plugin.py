from custom_pyqt6_designer.monkez_widgets import MonkezDateEdit

try:
    from plugin_factory import PluginSpec, create_plugin
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin


MonkezDateEditPlugin = create_plugin(
    PluginSpec(
        MonkezDateEdit,
        "MonkezDateEdit",
        "monkezDateEdit",
        "dateedit",
        "Themed date editor",
        "Date editor with calendar popup and configurable theme, colors, radius, and display format.",
    ),
    __name__,
)
