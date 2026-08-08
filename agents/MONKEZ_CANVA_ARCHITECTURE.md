# MonkezCanva architecture

Updated: 2026-08-08

## Product decision

`MonkezCanva` is a runtime-first `QWidget` backed by `QGraphicsView` and
`QGraphicsScene`. This keeps it portable, paint-efficient and independent of
WebEngine/JavaScript. The requested name is deliberately spelled `Canva`; do not
rename it to `Canvas` and break `.ui` forms.

The editor accepts both `Ctrl+D, E` (`Ctrl+D`, release Ctrl, then `E`) and
`Ctrl+D, Ctrl+E` (keep Ctrl held while pressing both letters). Both shortcuts
are scoped to the canvas's top-level window through `QShortcut.WindowShortcut`.
Applications with multiple canvases should enable the shortcut on only the
currently editable canvas.

`diagnosticMessage` reports shortcut activation, edit-mode state and toolbox
placement. The demo connects it to console and `canva_demo.log`; library users
can ignore the signal or route it into their own logger.

## Current layers

- `MonkezCanva`: public API, document persistence, properties and signals.
- `_CanvasView`: native zoom, click routing and blank-area right-button panning.
- `_CanvasScene`: background/grid painting.
- `_CanvasElement`: shape, node and chart rendering plus resize.
- `_CanvasConnector`: cubic edge tracking both endpoints.
- `_CanvasEditorToolbox`: compact frameless five-tab pane with a draggable custom
  header for element creation, deep inspection, layers, viewport and persistence.
- `_CanvasQuickToolbar`: viewport-owned floating Save/zoom/fit/alignment overlay;
  it never participates in `MonkezCanva` layout or changes view geometry.
- `monkez_10_canva_plugin.py`: Designer adapter and preview.

Elements and connectors use stable string IDs. Application code must retain IDs
rather than private graphics items.

Selection is an ordered ID set exposed by `selectedElementIds()` and
`selectionSetChanged(list)`. Alignment is one document mutation even though it
moves several graphics items, so autosave and Undo receive one coherent state.

## Persistence and trust boundary

Document format version 1 is JSON-only and does not evaluate Python. Loading
validates the format and supported element kinds. Future custom element plugins
need a registry/allowlist; importing module names from documents is unacceptable.

## Autosave and durable storage

Autosave is debounce-based. It updates the in-memory draft and bounded history;
when `persistenceKey` is configured it also writes the durable JSON. Explicit
session checkpoints remain process-local. Persistent saves copy media into the
application-data asset directory so a restart does not depend on a temporary
drag source.

## Roadmap

1. Clipboard, keyboard nudging and mixed-value multi-selection property editing.
2. Public element registry using schema + renderer/editor factories.
3. Typed ports, connector validation, orthogonal routing and auto layout.
4. Declarative data bindings and throttled live chart updates.
5. Optional `QGraphicsProxyWidget` adapter with explicit ownership.
6. Large-scene profiling, level-of-detail rendering and culling tests.
7. Collaboration after operation IDs and conflict semantics are stable.

## Verification focus

- Lazy import remains intact and runtime does not import Designer packages.
- JSON round trips preserve IDs, chart values, styles and connectors.
- View mode keeps items immovable; edit mode enables selection/movement.
- Designer discovers exactly one plugin class from the module.
- Gallery docs and preview cover the public widget surface.
