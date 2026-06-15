from custom_pyqt6_designer.monkez_widgets import MonkezSpinBox

try:
    from plugin_factory import PluginSpec, create_plugin
    from plugin_groups import GROUP_VALUES
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin
    from .plugin_groups import GROUP_VALUES


MonkezSpinBoxPlugin = create_plugin(
    PluginSpec(
        MonkezSpinBox,
        "MonkezSpinBox",
        "monkezSpinBox",
        "spinbox",
        "Themed integer spin box",
        "Integer input with configurable theme, colors, radius, range, step, and suffix/prefix.",
        group=GROUP_VALUES,
        properties_xml='  <property name="value"><number>25</number></property>',
    ),
    __name__,
)
