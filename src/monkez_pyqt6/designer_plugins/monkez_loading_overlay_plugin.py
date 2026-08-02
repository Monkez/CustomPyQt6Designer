from monkez_pyqt6.monkez_widgets import MonkezLoadingOverlay

try:
    from plugin_factory import PluginSpec, create_plugin
    from plugin_groups import GROUP_CONTAINERS
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin
    from .plugin_groups import GROUP_CONTAINERS


MonkezLoadingOverlayPlugin = create_plugin(
    PluginSpec(
        MonkezLoadingOverlay, "MonkezLoadingOverlay", "monkezLoadingOverlay", "loading",
        "Loading overlay surface", "Loading surface with spinner and status message.", 240, 150,
        properties_xml='  <property name="message"><string>Loading…</string></property>',
        group=GROUP_CONTAINERS,
    ), __name__
)
