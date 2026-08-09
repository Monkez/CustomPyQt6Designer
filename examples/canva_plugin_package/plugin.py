"""Standalone example copied into a project's .monkez_canva/plugins folder."""

from monkez_pyqt6.monkez_canva import ElementDefinition, component_plugin


PLUGIN_ID = "com.monkez.examples.packaged-notes"

PLUGIN = component_plugin(
    PLUGIN_ID,
    "Packaged Notes",
    "1.0.0",
    (
        ElementDefinition(
            "packaged_note",
            "Packaged note",
            "Project plugins",
            210,
            120,
            icon="text",
            defaults={
                "text": "Portable plugin note",
                "color": "#ff6b5f",
                "background": "#fff7f5",
                "priority": "normal",
            },
            schema={
                "properties": {
                    "priority": {
                        "type": "string",
                        "enum": ["low", "normal", "high"],
                    }
                }
            },
            plugin_id=PLUGIN_ID,
            plugin_version="1.0.0",
            capabilities={"content", "geometry", "appearance"},
        ),
    ),
    description="Minimal project-local package with declarative properties.",
    metadata={"license": "MIT", "example": True},
)
