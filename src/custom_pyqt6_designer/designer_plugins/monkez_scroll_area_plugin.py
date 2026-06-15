from custom_pyqt6_designer.monkez_widgets import MonkezScrollArea

try:
    from plugin_factory import PluginSpec, create_plugin
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin


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
    ),
    __name__,
)
