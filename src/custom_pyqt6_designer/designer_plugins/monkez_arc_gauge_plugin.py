from custom_pyqt6_designer.monkez_widgets import MonkezArcGauge

try:
    from plugin_factory import PluginSpec, create_plugin
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin


MonkezArcGaugePlugin = create_plugin(
    PluginSpec(
        MonkezArcGauge,
        "MonkezArcGauge",
        "monkezArcGauge",
        "arcgauge",
        "Arc status gauge",
        "Wide arc gauge with segmented mode and configurable warning and danger thresholds.",
        220,
        150,
        properties_xml='  <property name="value"><number>68</number></property>',
    ),
    __name__,
)
