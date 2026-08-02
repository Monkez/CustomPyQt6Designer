from monkez_pyqt6.monkez_widgets import MonkezLoadingIndicator

try:
    from plugin_factory import PluginSpec, create_plugin
    from plugin_groups import GROUP_DISPLAY
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin
    from .plugin_groups import GROUP_DISPLAY


MonkezLoadingIndicatorPlugin = create_plugin(
    PluginSpec(
        MonkezLoadingIndicator, "MonkezLoadingIndicator", "monkezLoadingIndicator", "loading",
        "Animated loading indicator", "Dependency-free themed spinner with configurable speed and stroke.",
        40, 40, group=GROUP_DISPLAY,
    ), __name__
)
