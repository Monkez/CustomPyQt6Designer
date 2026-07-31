from monkez_pyqt6.monkez_widgets import MonkezScrollArea

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
        properties_xml="""
  <property name="widgetResizable"><bool>true</bool></property>
""",
        children_xml="""
  <widget class="QWidget" name="scrollAreaWidgetContents">
   <property name="geometry">
    <rect>
     <x>0</x><y>0</y><width>258</width><height>178</height>
    </rect>
   </property>
  </widget>
""",
    ),
    __name__,
)
