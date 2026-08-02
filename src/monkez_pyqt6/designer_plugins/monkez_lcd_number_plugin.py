from monkez_pyqt6.monkez_widgets import MonkezLCDNumber

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
        "LCD display with decimal-point formatting, configurable palette, border and segment style.",
        180,
        72,
        properties_xml=(
            '  <property name="autoDigitCount"><bool>true</bool></property>\n'
            '  <property name="displayText"><string>1234.56</string></property>'
        ),
        group=GROUP_DISPLAY,
    ),
    __name__,
)
