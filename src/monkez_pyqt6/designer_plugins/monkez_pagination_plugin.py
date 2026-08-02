from monkez_pyqt6.monkez_widgets import MonkezPagination

try:
    from plugin_factory import PluginSpec, create_plugin
    from plugin_groups import GROUP_DISPLAY
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin
    from .plugin_groups import GROUP_DISPLAY


MonkezPaginationPlugin = create_plugin(
    PluginSpec(
        MonkezPagination,
        "MonkezPagination",
        "monkezPagination",
        "pagination",
        "Themed pagination control",
        "Pagination with Rounded, Pill, Minimal and Compact styles, ellipsis, keyboard control and item-based paging.",
        420,
        40,
        properties_xml=(
            '  <property name="pageCount"><number>12</number></property>\n'
            '  <property name="currentPage"><number>4</number></property>\n'
            '  <property name="styleIndex"><number>0</number></property>'
        ),
        group=GROUP_DISPLAY,
    ),
    __name__,
)
