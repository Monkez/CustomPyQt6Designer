from monkez_pyqt6.monkez_widgets import MonkezLoadingIndicator

try:
    from plugin_factory import PluginSpec, create_plugin
    from plugin_groups import GROUP_FEEDBACK
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin
    from .plugin_groups import GROUP_FEEDBACK


MonkezLoadingIndicatorPlugin = create_plugin(
    PluginSpec(
        MonkezLoadingIndicator, "MonkezLoadingIndicator", "monkezLoadingIndicator", "loading",
        "Animated loading indicator", "Dependency-free themed spinner with configurable speed and stroke.",
        40, 40, group=GROUP_FEEDBACK,
    ), __name__
)
