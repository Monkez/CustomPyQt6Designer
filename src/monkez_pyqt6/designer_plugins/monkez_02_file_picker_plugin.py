from monkez_pyqt6.monkez_widgets import MonkezFilePicker

try:
    from plugin_factory import PluginSpec, create_plugin
    from plugin_groups import GROUP_INPUTS
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin
    from .plugin_groups import GROUP_INPUTS


MonkezFilePickerPlugin = create_plugin(
    PluginSpec(
        MonkezFilePicker, "MonkezFilePicker", "monkezFilePicker", "file",
        "File and directory picker", "Path input with open, save and directory dialog modes.",
        340, 40,
        properties_xml='  <property name="placeholderText"><string>Select a file…</string></property>',
        group=GROUP_INPUTS,
    ), __name__
)
