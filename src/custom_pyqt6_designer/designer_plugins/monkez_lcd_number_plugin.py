from custom_pyqt6_designer.monkez_widgets import MonkezLCDNumber

try:
    from plugin_factory import PluginSpec, create_plugin
    from plugin_groups import GROUP_DISPLAY
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin
    from .plugin_groups import GROUP_DISPLAY


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
        group=GROUP_DISPLAY,
    ),
    __name__,
)
