# MonkezCanva architecture

Updated: 2026-08-08

## Product decision

`MonkezCanva` is a runtime-first `QWidget` backed by `QGraphicsView` and
`QGraphicsScene`. This keeps it portable, paint-efficient and independent of
WebEngine/JavaScript. The requested name is deliberately spelled `Canva`; do not
rename it to `Canvas` and break `.ui` forms.

The editor chord is `Ctrl+D, E` (`Ctrl+D`, then `E`), scoped to the canvas's top
level window through `QShortcut.WindowShortcut`. Applications with multiple
canvases should enable the shortcut on only the currently editable canvas.

## Current layers

- `MonkezCanva`: public API, document persistence, properties and signals.
- `_CanvasView`: native zoom and click routing.
- `_CanvasScene`: background/grid painting.
- `_CanvasElement`: shape, node and chart rendering plus resize.
- `_CanvasConnector`: cubic edge tracking both endpoints.
- `_CanvasToolbox`: owned `Qt.Tool` palette.
- `monkez_10_canva_plugin.py`: Designer adapter and preview.

Elements and connectors use stable string IDs. Application code must retain IDs
rather than private graphics items.

## Persistence and trust boundary

Document format version 1 is JSON-only and does not evaluate Python. Loading
validates the format and supported element kinds. Future custom element plugins
need a registry/allowlist; importing module names from documents is unacceptable.

## Roadmap

1. Command-based undo/redo, clipboard and keyboard nudging.
2. Public element registry using schema + renderer/editor factories.
3. Typed ports, connector validation, orthogonal routing and auto layout.
4. Property inspector with mixed-value multi-selection editing.
5. Declarative data bindings and throttled live chart updates.
6. Optional `QGraphicsProxyWidget` adapter with explicit ownership.
7. Large-scene profiling, level-of-detail rendering and culling tests.
8. Collaboration after operation IDs and conflict semantics are stable.

## Verification focus

- Lazy import remains intact and runtime does not import Designer packages.
- JSON round trips preserve IDs, chart values, styles and connectors.
- View mode keeps items immovable; edit mode enables selection/movement.
- Designer discovers exactly one plugin class from the module.
- Gallery docs and preview cover the public widget surface.
