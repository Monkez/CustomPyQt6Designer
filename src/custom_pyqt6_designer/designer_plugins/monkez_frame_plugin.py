from custom_pyqt6_designer.monkez_widgets import MonkezFrame

try:
    from plugin_factory import PluginSpec, create_plugin
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin


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
    ),
    __name__,
)
