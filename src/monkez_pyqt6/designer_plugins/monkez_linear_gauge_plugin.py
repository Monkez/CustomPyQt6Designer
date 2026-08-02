from monkez_pyqt6.monkez_widgets import MonkezLinearGauge

try:
    from plugin_factory import PluginSpec, create_plugin
    from plugin_groups import GROUP_DISPLAY
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin
    from .plugin_groups import GROUP_DISPLAY


MonkezLinearGaugePlugin = create_plugin(
    PluginSpec(
        MonkezLinearGauge,
        "MonkezLinearGauge",
        "monkezLinearGauge",
        "lineargauge",
        "Linear target gauge",
        "Horizontal or vertical gauge with target marker, labels, custom thickness, colors, and shadow.",
        260,
        90,
        group=GROUP_DISPLAY,
        properties_xml='  <property name="value"><number>68</number></property>',
    ),
    __name__,
)
