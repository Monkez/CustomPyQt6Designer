from custom_pyqt6_designer.monkez_widgets import MonkezScrollArea

try:
    from plugin_factory import PluginSpec, create_plugin
    from plugin_groups import GROUP_CONTAINERS
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin
    from .plugin_groups import GROUP_CONTAINERS


MonkezScrollAreaPlugin = create_plugin(
    PluginSpec(
        MonkezScrollArea,
        "MonkezScrollArea",
        "monkezScrollArea",
        "scrollarea",
        "Themed scroll area container",
        "Resizable scroll area with themed viewport and compact configurable scrollbars.",
        260,
        180,
        container=True,
        group=GROUP_CONTAINERS,
    ),
    __name__,
)
