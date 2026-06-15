from custom_pyqt6_designer.monkez_widgets import MonkezFrame

try:
    from plugin_factory import PluginSpec, create_plugin
    from plugin_groups import GROUP_CONTAINERS
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin
    from .plugin_groups import GROUP_CONTAINERS


MonkezFramePlugin = create_plugin(
    PluginSpec(
        MonkezFrame,
        "MonkezFrame",
        "monkezFrame",
        "frame",
        "Themed frame container",
        "Surface container with configurable theme, border, radius, colors, and elevation.",
        240,
        160,
        container=True,
        group=GROUP_CONTAINERS,
    ),
    __name__,
)
