# MonkezCanva architecture

Updated: 2026-08-09

The complete approved expansion sequence and module extraction contract now live
in `MONKEZ_CANVA_IMPLEMENTATION_PLAN.md`; the user-facing milestone roadmap is
`../docs/MONKEZ_CANVA_MASTER_ROADMAP.md`. Future feature work must follow that
dependency order rather than extending the current monolith opportunistically.

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

- `monkez_pyqt6.monkez_canva.CanvasDocument`: Qt-free canonical scene state with
  immutable scene/element/connector/port/group/resource records, JSON validation,
  revision numbers and granular `OperationEvent` subscriptions.
- `MonkezCanva`: public API, document persistence, properties and signals.
- `_CanvasView`: native zoom, click routing and blank-area right-button panning.
- `_CanvasScene`: background/grid painting.
- `_CanvasElement`: shapes, node, splitter, charts, media and unified single/multi-segment
  line rendering plus resize. Arrowheads are line options, not a separate kind.
- `_CanvasConnector`: selectable/code-addressable `QGraphicsObject` with stable ID,
  endpoint tracking, straight/bezier/orthogonal/polyline routes, stroke styles,
  one/two-way arrows and timer-driven signal-flow/packet animation.
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

Node and splitter ports are embedded JSON-safe records (`id`, `mode`, `side`, `label`, optional
normalized `position`). Input and output share a triangular marker distinguished
by semantic color and opposing inward/outward direction; free uses a diamond. `_CanvasView`
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

Line and connector animation share `_paint_path_effect()` with flow, pulse, glow,
particles and packet modes. Packet instances have stable message IDs and monotonic
travel timing. `MonkezCanva` tracks pending terminal branches; arrival at a splitter
fans the same logical message into all unvisited output connectors, and emits one
final `messageArrived` only after the branch count reaches zero. This defines the
blocking boundary for `send_a_message(..., wait_to_end=True)` while a nested Qt
event loop keeps painting and timers responsive.

Selection is an ordered ID set exposed by `selectedElementIds()` and
`selectionSetChanged(list)`. Alignment is one document mutation even though it
moves several graphics items, so autosave and Undo receive one coherent state.
Horizontal/vertical distribution follows the same rule and requires at least
three elements.

## Canonical document bridge

`MonkezCanva` owns or attaches one `CanvasDocument` through `setDocumentModel()`.
Multiple canvas instances may subscribe to the same model. A direct model change
is dispatched incrementally to every attached view. Add/update/remove/rename
operations preserve unrelated graphics objects, while property and ID changes
preserve the affected object's identity, selection and viewport. Public element
and connector add/update/remove/rename APIs commit to the model first. A direct
graphics interaction still reconciles rendered state back into immutable records
and emits record-level events through `documentOperation`.

## Command history

`MonkezCanva` owns a bounded `QUndoStack`. `_canva_commands.py` computes minimal
before/after patches for only the changed scene or records, then applies them by
building a candidate from current canonical state and reconciling atomically.
Commands never retain a whole-document snapshot. Element/connector rename uses
an explicit command so item identity survives undo and redo.

Model-first API calls push commands before mutation. Legacy graphics gestures
reconcile once, then push an `already_applied` command. Consecutive changes to the
same record merge for 800 ms, covering drag, resize and Inspector typing. Compound
selection operations use `beginCommandMacro()`/`endCommandMacro()`. External
changes made directly to a shared `CanvasDocument` intentionally do not enter a
particular view's local history. Persistent/document save marks the stack clean;
autosave draft does not pretend durable changes were saved.

## Selection clipboard and mixed Inspector

`monkez_canva/clipboard.py` defines a Qt-free, versioned subgraph contract. Copy
adds endpoint dependencies for explicitly selected connectors and preserves every
connector whose endpoints are both selected. Decode enforces a 5 MiB/10,000-object
boundary, finite JSON, global IDs and included endpoints. Paste accepts only
registered component types, allocates collision-free IDs, remaps connector
endpoints, offsets scene-space waypoints and commits the whole subgraph as one
document command. The system clipboard transport is a dedicated MIME type; JSON
never selects or imports executable Python.

Keyboard nudge updates canonical records first and shares a selection-scoped
merge key, so rapid key repeats form one undo step. Snap-to-grid applies only to
direct graphics gestures, never while model operations are rendered. The
multi-selection Inspector maintains an explicit mixed state per field; sync does
not manufacture values, and auto-apply sends only fields dirtied by the user.

## Persistence and trust boundary

Document format version 1 is JSON-only and does not evaluate Python. Loading
validates the stable structure against the public Draft 2020-12 schema contract.
`schema.py` owns document-version migration order; component migrations remain in
the trusted registry. Future custom element plugins use the registry/allowlist;
importing module names from documents is unacceptable.

Documents newer than the runtime are parsed only through the known structural
subset and retain their source version/extensions. The model rejects every
mutation with `PermissionError`. A version-1 document containing a component
schema newer than its registered definition is read-only at the view boundary.
The pane disables Add, Inspect, View and Save while leaving Layers and non-mutating
navigation/runtime visualization available. This prevents an older runtime from
normalizing or overwriting unknown data.

## Component registry and plugin boundary

Every canvas owns a clone of the Qt-free built-in `ElementRegistry`. An
`ElementDefinition` declares its stable type ID, palette metadata, default size
and values, capability set, JSON-schema subset, component schema version,
contiguous migrations and plugin ownership. Built-ins use native painting plus
capability-driven standard Inspector sections; extensions may supply explicit
renderer and Inspector factories without changing `monkez_canva.py`.

Documents never contain Python module or callable names. Registration happens in
trusted application/plugin code. Records are migrated, defaulted and validated
before entering a canvas. Factory exceptions are contained at the Qt boundary:
renderer failures paint an error placeholder and Inspector failures emit
diagnostics. Unloading a plugin removes its factories but preserves canonical
records. Re-registering a previously missing type replaces its placeholder and
restores the renderer without changing object IDs.

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

Every JSON write is serialized and validated before same-directory atomic replace.
A valid previous primary becomes `<name>.json.bak`; a corrupt primary never replaces
an existing valid backup. Loaders fall back to that backup and emit `recoveryLoaded`.
Managed image/GIF/background/packet/resource files are copied atomically and listed
under `assetManifest` with SHA-256 and byte size. Loading verifies the manifest,
emits `assetIntegrityChecked`, and keeps warnings accessible through
`assetIntegrityIssues()`; integrity warnings do not execute or repair untrusted data.

Scene version 1 also persists grid visibility/size/style/colors and background
color/image/mode. Grid renderers are lines, dots and crosses; background modes
are fit, fill and non-aspect-preserving scale.

## Shared animation clock

`CanvasAnimationScheduler` owns one precise timer for the whole canvas. Animated
lines, connectors, packets and public `animateElement()` tweens register weakly
with that scheduler instead of allocating a timer per item. Each tick computes
the visible scene rectangle and requests repaint only for intersecting targets.
Decorative effects and packet loops pause while the canvas is hidden; explicitly
sent packets continue to completion so `wait_to_end=True` cannot deadlock. Public
`animationStats()` and `animationFrameInterval()` expose lightweight diagnostics
without leaking scheduler implementation details.

## Roadmap

1. Clipboard, keyboard nudging and true mixed-value property editing.
2. Searchable palette, command palette and contextual actions.
3. Typed ports, advanced routing and group/subflow rendering.
4. Port data types, cardinality rules, obstacle-avoiding routing and auto layout.
5. Declarative data bindings and throttled live chart updates.
6. Optional `QGraphicsProxyWidget` adapter with explicit ownership.
7. Large-scene profiling, level-of-detail rendering and culling tests.
8. Collaboration after operation IDs and conflict semantics are stable.

## Verification focus

- Lazy import remains intact and runtime does not import Designer packages.
- JSON round trips preserve IDs, chart values, unified line points, node port
  schemas and advanced connector routes, arrows, styles, animation and endpoint ports.
- View mode keeps items immovable; edit mode enables selection/movement.
- Designer discovers exactly one plugin class from the module.
- Gallery docs and preview cover the public widget surface.
