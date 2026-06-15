from custom_pyqt6_designer.monkez_widgets import MonkezTimeEdit

try:
    from plugin_factory import PluginSpec, create_plugin
    from plugin_groups import GROUP_VALUES
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin
    from .plugin_groups import GROUP_VALUES


MonkezTimeEditPlugin = create_plugin(
    PluginSpec(
        MonkezTimeEdit,
        "MonkezTimeEdit",
        "monkezTimeEdit",
        "timeedit",
        "Themed time editor",
        "Time editor with configurable theme, colors, radius, sections, and display format.",
        group=GROUP_VALUES,
    ),
    __name__,
)
