from custom_pyqt6_designer.monkez_widgets import MonkezScrollArea

try:
    from plugin_factory import PluginSpec, create_plugin
    from plugin_groups import GROUP_CONTAINERS
    from scroll_area_container import register_scroll_area_container
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin
    from .plugin_groups import GROUP_CONTAINERS
    from .scroll_area_container import register_scroll_area_container


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
        extra_initializer=register_scroll_area_container,
    ),
    __name__,
)
