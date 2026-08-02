from monkez_pyqt6.monkez_widgets import MonkezBreadcrumb

try:
    from plugin_factory import PluginSpec, create_plugin
    from plugin_groups import GROUP_NAVIGATION
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin
    from .plugin_groups import GROUP_NAVIGATION


MonkezBreadcrumbPlugin = create_plugin(
    PluginSpec(
        MonkezBreadcrumb, "MonkezBreadcrumb", "monkezBreadcrumb", "breadcrumb",
        "Breadcrumb navigation", "Clickable hierarchical path with configurable separator and active item.",
        300, 36,
        properties_xml='  <property name="items"><string>Home | Cameras | Camera 01</string></property>',
        group=GROUP_NAVIGATION,
    ), __name__
)
