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
- `_CanvasElement`: shapes, node, charts, media and unified single/multi-segment
  line rendering plus resize. Arrowheads are line options, not a separate kind.
- `_CanvasConnector`: selectable/code-addressable `QGraphicsObject` with stable ID,
  endpoint tracking, straight/bezier/orthogonal/polyline routes, stroke styles,
  one/two-way arrows and timer-driven signal-flow animation.
- `_CanvasEditorToolbox`: compact frameless five-tab pane with a draggable custom
  header for element creation, deep inspection, layers, viewport and persistence.
- `_CanvasQuickToolbar`: canvas-owned floating Save/zoom/fit/alignment overlay;
  it is a sibling above the view, never participates in layout and cannot be
  scrolled by `QGraphicsView::scrollContentsBy` while the scene is panned.
- `_canvas_icon()`: dependency-free QPainter icon factory shared by every pane
  and floatbar action; no external icon assets are required at packaging time.
- `monkez_10_canva_plugin.py`: Designer adapter and preview.

Elements and connectors use stable string IDs. Application code must retain IDs
rather than private graphics items.

Node ports are embedded JSON-safe records (`id`, `mode`, `side`, `label`, optional
normalized `position`). Input and output share a triangular marker distinguished
by semantic color; free uses a diamond. `_CanvasView`
performs port hit-testing before normal scene selection, paints a transient cubic
preview, validates direction through `connectPorts()`, then creates a normal
selectable connector carrying `sourcePort` and `targetPort`. Old `arrow` and
`polyline` element documents normalize to `line` during load.

Click signals deliberately separate domains: `elementClicked`, `connectorClicked`
and union signal `objectClicked`. Generic visual feedback must call
`highlightObject`; this prevents a connector ID reaching element-only APIs.

The Inspector is schema-by-kind rather than one generic form: connector endpoint
and signal controls are hidden for ordinary elements; media, chart, geometry,
content, stroke and color groups appear only where meaningful. Connector endpoint
changes disconnect the old element signals and attach the new pair without
replacing the connector ID. Controls auto-apply through a guarded single-shot
timer: direct choices apply immediately, while typing is briefly debounced and
invalid partial JSON is rejected through diagnostics instead of escaping the slot.

Selection is an ordered ID set exposed by `selectedElementIds()` and
`selectionSetChanged(list)`. Alignment is one document mutation even though it
moves several graphics items, so autosave and Undo receive one coherent state.

## Persistence and trust boundary

Document format version 1 is JSON-only and does not evaluate Python. Loading
validates the format and supported element kinds. Future custom element plugins
need a registry/allowlist; importing module names from documents is unacceptable.

## Autosave and durable storage

Autosave is debounce-based. It updates the in-memory draft and bounded history;
when `persistenceKey` is configured it writes `.monkez_canva/<key>.json` under
the detected/explicit project root. Managed element media and background images
are copied below `.monkez_canva/assets/<key>/`, while JSON stores POSIX-style
relative paths. Moving the whole project therefore preserves loadability.
Legacy AppData documents and absolute paths remain readable and are migrated on
first load. Setting a persistence key schedules a safe auto-load after property
configuration; it proceeds only while the canvas is empty, so application-created
objects are never silently replaced. Explicit session checkpoints remain process-local.

Scene version 1 also persists grid visibility/size/style/colors and background
color/image/mode. Grid renderers are lines, dots and crosses; background modes
are fit, fill and non-aspect-preserving scale.

## Roadmap

1. Clipboard, keyboard nudging and mixed-value multi-selection property editing.
2. Public element registry using schema + renderer/editor factories.
3. Port data types, cardinality rules, obstacle-avoiding routing and auto layout.
4. Declarative data bindings and throttled live chart updates.
5. Optional `QGraphicsProxyWidget` adapter with explicit ownership.
6. Large-scene profiling, level-of-detail rendering and culling tests.
7. Collaboration after operation IDs and conflict semantics are stable.

## Verification focus

- Lazy import remains intact and runtime does not import Designer packages.
- JSON round trips preserve IDs, chart values, unified line points, node port
  schemas and advanced connector routes, arrows, styles, animation and endpoint ports.
- View mode keeps items immovable; edit mode enables selection/movement.
- Designer discovers exactly one plugin class from the module.
- Gallery docs and preview cover the public widget surface.
