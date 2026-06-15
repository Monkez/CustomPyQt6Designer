from custom_pyqt6_designer.monkez_widgets import MonkezDoubleSpinBox

try:
    from plugin_factory import PluginSpec, create_plugin
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin


MonkezDoubleSpinBoxPlugin = create_plugin(
    PluginSpec(
        MonkezDoubleSpinBox,
        "MonkezDoubleSpinBox",
        "monkezDoubleSpinBox",
        "doublespinbox",
        "Themed decimal spin box",
        "Decimal input with configurable theme, colors, radius, precision, range, and step.",
        properties_xml='  <property name="value"><double>25.500000000000000</double></property>',
    ),
    __name__,
)
