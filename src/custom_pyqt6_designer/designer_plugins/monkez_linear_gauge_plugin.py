from custom_pyqt6_designer.monkez_widgets import MonkezLinearGauge

try:
    from plugin_factory import PluginSpec, create_plugin
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin


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
        properties_xml='  <property name="value"><number>68</number></property>',
    ),
    __name__,
)
