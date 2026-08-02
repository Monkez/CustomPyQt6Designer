from monkez_pyqt6.monkez_widgets import MonkezStatusBadge

try:
    from plugin_factory import PluginSpec, create_plugin
    from plugin_groups import GROUP_DISPLAY
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin
    from .plugin_groups import GROUP_DISPLAY


MonkezStatusBadgePlugin = create_plugin(
    PluginSpec(
        MonkezStatusBadge, "MonkezStatusBadge", "monkezStatusBadge", "badge",
        "Semantic status badge", "Info, success, warning, error and neutral status badge.", 100, 30,
        properties_xml='  <property name="badgeText"><string>Online</string></property>',
        group=GROUP_DISPLAY,
    ), __name__
)
