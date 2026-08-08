from monkez_pyqt6.monkez_widgets import MonkezCanva

try:
    from plugin_factory import PluginSpec, create_plugin
    from plugin_groups import GROUP_CANVAS
except ModuleNotFoundError:
    from .plugin_factory import PluginSpec, create_plugin
    from .plugin_groups import GROUP_CANVAS


def _setup_preview(widget):
    source = widget.addNode("Input", -140, -45)
    target = widget.addNode("Output", 100, -45)
    widget.connectElements(source, target)


MonkezCanvaPlugin = create_plugin(
    PluginSpec(
        MonkezCanva,
        "MonkezCanva",
        "monkezCanva",
        "frame",
        "Interactive canvas, chart and flow-diagram editor",
        "Runtime-editable scene with a floating element palette, charts, nodes, connectors and JSON persistence.",
        640,
        420,
        themed=False,
        group=GROUP_CANVAS,
        setup_widget=_setup_preview,
    ),
    __name__,
)
