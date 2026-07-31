from monkez_pyqt6.monkez_widgets import MonkezSplashScreen

try:
    from plugin_factory import PluginSpec, create_plugin
    from plugin_groups import GROUP_CONTAINERS
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin
    from .plugin_groups import GROUP_CONTAINERS


MonkezSplashScreenPlugin = create_plugin(
    PluginSpec(
        MonkezSplashScreen,
        "MonkezSplashScreen",
        "monkezSplashScreen",
        "splash",
        "Designer-ready animated application splash screen",
        "Transparent PNG splash container with app information, progress, spinner, and runtime controller support.",
        680,
        400,
        container=True,
        properties_xml="""
  <property name="appName"><string>Monkez Application</string></property>
  <property name="appVersion"><string>Version 1.0</string></property>
  <property name="statusText"><string>Starting...</string></property>
  <property name="progress"><number>25</number></property>
  <property name="showProgress"><bool>true</bool></property>
  <property name="showSpinner"><bool>true</bool></property>
        """,
        group=GROUP_CONTAINERS,
        palette_visible=False,
    ),
    __name__,
)
