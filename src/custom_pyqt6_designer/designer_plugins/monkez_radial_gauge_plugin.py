from custom_pyqt6_designer.monkez_widgets import MonkezRadialGauge

try:
    from plugin_factory import PluginSpec, create_plugin
    from plugin_groups import GROUP_GAUGES
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin
    from .plugin_groups import GROUP_GAUGES


MonkezRadialGaugePlugin = create_plugin(
    PluginSpec(
        MonkezRadialGauge,
        "MonkezRadialGauge",
        "monkezRadialGauge",
        "radialgauge",
        "Radial dashboard gauge",
        "Instrument gauge with needle, major/minor ticks, scale labels, themes, colors, and shadow.",
        220,
        220,
        group=GROUP_GAUGES,
        properties_xml='  <property name="value"><number>68</number></property>',
    ),
    __name__,
)
