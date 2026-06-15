from custom_pyqt6_designer.monkez_widgets import MonkezSpinBox

try:
    from plugin_factory import PluginSpec, create_plugin
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin


MonkezSpinBoxPlugin = create_plugin(
    PluginSpec(
        MonkezSpinBox,
        "MonkezSpinBox",
        "monkezSpinBox",
        "spinbox",
        "Themed integer spin box",
        "Integer input with configurable theme, colors, radius, range, step, and suffix/prefix.",
        properties_xml='  <property name="value"><number>25</number></property>',
    ),
    __name__,
)
