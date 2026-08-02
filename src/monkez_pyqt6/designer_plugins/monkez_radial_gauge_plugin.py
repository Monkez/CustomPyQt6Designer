from monkez_pyqt6.monkez_widgets import MonkezRadialGauge

try:
    from plugin_factory import PluginSpec, create_plugin
    from plugin_groups import GROUP_DISPLAY
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin
    from .plugin_groups import GROUP_DISPLAY


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
        group=GROUP_DISPLAY,
        properties_xml='  <property name="value"><number>68</number></property>',
    ),
    __name__,
)
