from custom_pyqt6_designer.monkez_widgets import MonkezDial

try:
    from plugin_factory import PluginSpec, create_plugin
    from plugin_groups import GROUP_VALUES
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin
    from .plugin_groups import GROUP_VALUES


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
        group=GROUP_VALUES,
        properties_xml='  <property name="value"><number>35</number></property>',
    ),
    __name__,
)
