from monkez_pyqt6.monkez_widgets import MonkezSegmentedControl

try:
    from plugin_factory import PluginSpec, create_plugin
    from plugin_groups import GROUP_NAVIGATION
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin
    from .plugin_groups import GROUP_NAVIGATION


MonkezSegmentedControlPlugin = create_plugin(
    PluginSpec(
        MonkezSegmentedControl, "MonkezSegmentedControl", "monkezSegmentedControl", "segments",
        "Segmented navigation", "Mutually-exclusive segments configured through a pipe-separated items property.",
        280, 40,
        properties_xml='  <property name="items"><string>Camera | Result | History</string></property>',
        group=GROUP_NAVIGATION,
    ), __name__
)
