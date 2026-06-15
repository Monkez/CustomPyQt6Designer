from custom_pyqt6_designer.monkez_widgets import MonkezGroupBox

try:
    from plugin_factory import PluginSpec, create_plugin
    from plugin_groups import GROUP_CONTAINERS
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin
    from .plugin_groups import GROUP_CONTAINERS


MonkezGroupBoxPlugin = create_plugin(
    PluginSpec(
        MonkezGroupBox,
        "MonkezGroupBox",
        "monkezGroupBox",
        "groupbox",
        "Polished themed group box",
        "Card-style group container with header, subtitle, accent, custom indicator, elevation, and deep color controls.",
        280,
        180,
        container=True,
        group=GROUP_CONTAINERS,
        properties_xml=(
            '  <property name="title"><string>Account settings</string></property>\n'
            '  <property name="subtitle"><string>Manage profile and preferences</string></property>'
        ),
    ),
    __name__,
)
