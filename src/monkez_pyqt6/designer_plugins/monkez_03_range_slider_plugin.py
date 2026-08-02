from monkez_pyqt6.monkez_widgets import MonkezRangeSlider

try:
    from plugin_factory import PluginSpec, create_plugin
    from plugin_groups import GROUP_VALUES
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin
    from .plugin_groups import GROUP_VALUES


MonkezRangeSliderPlugin = create_plugin(
    PluginSpec(
        MonkezRangeSlider, "MonkezRangeSlider", "monkezRangeSlider", "slider",
        "Two-handle range slider", "Horizontal or vertical integer range selector with two handles.",
        240, 40,
        properties_xml=(
            '  <property name="lowerValue"><number>25</number></property>\n'
            '  <property name="upperValue"><number>75</number></property>'
        ), group=GROUP_VALUES,
    ), __name__
)
