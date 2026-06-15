from custom_pyqt6_designer.monkez_widgets import MonkezLCDNumber

try:
    from plugin_factory import PluginSpec, create_plugin
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin


MonkezLCDNumberPlugin = create_plugin(
    PluginSpec(
        MonkezLCDNumber,
        "MonkezLCDNumber",
        "monkezLCDNumber",
        "lcd",
        "Themed LCD number",
        "LCD display with configurable palette, background, border, radius, digit count, and segment style.",
        180,
        72,
    ),
    __name__,
)
