from monkez_pyqt6.monkez_widgets import MonkezTable

try:
    from plugin_factory import PluginSpec, create_plugin
    from plugin_groups import GROUP_DISPLAY
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin
    from .plugin_groups import GROUP_DISPLAY


def _setup_preview(widget: MonkezTable) -> None:
    widget.setColumns(
        [
            {"key": "name", "title": "Name", "width": 170},
            {"key": "status", "title": "Status", "type": "badge", "width": 110},
            {"key": "progress", "title": "Progress", "type": "progress", "width": 140},
        ]
    )
    widget.setRows(
        [
            {"name": "Camera 01", "status": "Online", "progress": 84},
            {"name": "Camera 02", "status": "Offline", "progress": 36},
        ]
    )


MonkezTablePlugin = create_plugin(
    PluginSpec(
        MonkezTable,
        "MonkezTable",
        "monkezTable",
        "table",
        "Professional data table",
        "High-performance model/view table with search, filters, sorting, pagination and server mode.",
        720,
        420,
        properties_xml=(
            '  <property name="styleIndex"><number>0</number></property>\n'
            '  <property name="densityIndex"><number>1</number></property>\n'
            '  <property name="pageSize"><number>20</number></property>'
        ),
        group=GROUP_DISPLAY,
        setup_widget=_setup_preview,
    ),
    __name__,
)
