from monkez_pyqt6.monkez_widgets import MonkezArcGauge

try:
    from plugin_factory import PluginSpec, create_plugin
    from plugin_groups import GROUP_DISPLAY
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin
    from .plugin_groups import GROUP_DISPLAY


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
        group=GROUP_DISPLAY,
        properties_xml='  <property name="value"><number>68</number></property>',
    ),
    __name__,
)
