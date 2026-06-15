from custom_pyqt6_designer.monkez_widgets import MonkezDial

try:
    from plugin_factory import PluginSpec, create_plugin
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin


MonkezDialPlugin = create_plugin(
    PluginSpec(
        MonkezDial,
        "MonkezDial",
        "monkezDial",
        "dial",
        "Themed dial",
        "Antialiased dial with configurable track, value, handle, text, and value display.",
        120,
        120,
        properties_xml='  <property name="value"><number>35</number></property>',
    ),
    __name__,
)
