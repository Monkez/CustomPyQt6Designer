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
particles and packet modes. Visual packet instances keep only ID, pixmap, duration
and monotonic start time. The authoritative transient lifecycle lives in the
Qt-free `packet_runtime.py`: `PacketRuntime` owns `MessageTicket` state, branch
selection, priority order, hop TTL, wall-clock timeout, breakpoints and a bounded
sequence trace. Payload and runtime metadata never cross into `CanvasDocument`.

`MonkezCanva` maps segment start/arrival to graphics packets and runtime events.
Splitter propagation asks the runtime for `all`, `first` or `round_robin` branches;
completion emits one final `messageArrived` only after selected branches reach
zero pending segments. `send_a_message()` remains the string-ID compatibility API,
`sendMessageTicket()` is non-blocking, and `sendMessageAsync()` awaits the same
ticket in a Qt/asyncio-integrated host. Blocking compatibility uses a nested Qt
event loop that exits for every terminal state, including timeout/cancellation.

Breakpoint arrivals are queued by the Qt adapter, not the pure runtime. Pause
shifts visual packet start times by each scheduler delta, so paint progress freezes
without creating per-packet timers. Step consumes one queued arrival; Resume drains
the queue with breakpoint bypass and returns tickets to in-flight state. The
detached `_CanvasRuntimeDebugger` is only a signal/API client and owns no runtime
truth, allowing applications to replace it with their own debugger safely.

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

## Registry-driven editor discovery

`monkez_canva/palette.py` is the Qt-free query layer for component discovery. It
normalizes ordered preferences and ranks registry metadata across label, stable
type ID, category, capabilities and plugin owner. The Qt pane only materializes
the returned entries; registering a component therefore feeds search, categories,
favorite controls and Ctrl+K commands without adding UI-specific branches.

Favorites and a bounded 12-entry recent list are scene properties, so they follow
portable project persistence and shared documents. Adding an element updates the
recent list inside the same candidate document mutation; Undo/Redo remains one
coherent user action. The command palette rebuilds on open from registry, selection,
clipboard MIME, read-only state and history, and stores callbacks only in trusted
runtime UI—not in JSON.

## Snapping and contextual manipulation

`monkez_canva/snapping.py` is Qt-free and accepts simple scene rectangles and
port points. It resolves each axis independently within a bounded threshold and
returns semantic guides; Qt owns only candidate collection and foreground
painting. Scene keys `snapTargets`, `snapDistance` and `smartGuidesVisible` are
portable document state. Grid eligibility remains compatible with `snapToGrid`.

Context menus are constructed by `createContextMenu()` so hosts and tests can
inspect the same availability rules used by the visible menu. Blank right-click
opens it only when pointer movement stays below the pan threshold. Equal-size
operations update canonical element records through one document command.

## Outline, visibility and viewport navigation

Element and connector records persist explicit `locked` and `hidden` booleans.
The graphics projection derives selectable/movable/visible flags centrally in
`_sync_object_states()`; connectors also follow endpoint visibility. Isolation
is deliberately view-local (`_isolated_ids`) and never overwrites document
visibility. Batch state changes are one patch-based undo command.

Viewport bookmarks live in the scene as bounded JSON records containing stable
ID, label, center and zoom. The minimap is a canvas child overlay, not a layout
row or scene item, so canvas transforms never move it. It renders a lightweight
overview and viewport rectangle and maps click/drag positions back to scene space.

## Connector routing projection

`monkez_canva/routing.py` owns Qt-free lane allocation, orthogonal waypoint
expansion, point normalization, rectangular obstacle routing and proper segment
intersection. Connector records persist `waypoints`, `cornerRadius`, `label`,
`labelPosition`, `parallelSpacing`, obstacle clearance, bridge and bus options.
The obstacle router uses a deterministic rectilinear visibility grid plus A* with
a bend penalty. The Qt projection builds rounded paths, stable symmetric parallel
lanes, explicit self-loops and cached crossing bridges; animation, packets, hit
testing and arrowheads all consume the same final path.

Waypoint handles are child graphics objects created only for a selected editable
connector. Dragging updates preview geometry; release commits one model command.
Double-click adds/removes reroute points through public model-first APIs. Existing
connector IDs and endpoint references never change during rerouting.

`route=auto` derives obstacles from visible non-endpoint element scene bounds and
reruns when element geometry changes. Bridge caches are keyed by a canvas-wide
routing revision. `busStyle=trunk|double` changes only projection stroke layers;
`busId` remains portable semantic metadata for later runtime bus grouping.

## Typed port contract and transient values

`monkez_canva/typed_ports.py` is the Qt-free authority for port normalization,
orientation, cardinality, type/unit compatibility and runtime value validation.
`PortModel` stores the normalized contract; `CanvasDocument` revalidates attached
connectors when element ports change and rolls an invalid update back before it
can emit an operation. Connector updates exclude their own ID from counts.

The graphics layer calls the same functions through `portCompatibility()`.
Connection drag feedback is projection-only state held by `_CanvasElement`; it is
cleared on release or Escape and never enters `to_dict()`. Green means a direct
match, purple a declared conversion, red a rejected target and blue the origin.
The preview pen and diagnostic text use the exact returned compatibility result.

`_port_runtime_values[(element_id, port_id)]` is intentionally canvas-local.
Rename remaps its keys; port/element removal and clear discard it. Public setters
validate values and emit `portRuntimeValueChanged`, while serialization contains
only `defaultValue`, never the current runtime value. This boundary is required
for shared documents, Undo and durable save to remain deterministic.

## Groups, swimlanes and subflows

Group records are projected by `_CanvasGroup`, a low-Z selectable graphics object
that never becomes canonical state. `kind=frame|swimlane|subflow` selects only the
projection style; members remain stable element or nested-group IDs. The Qt-free
`groups.py` layer computes padded bounds, flattens descendants and rejects missing
references, unsupported kinds and direct/indirect cycles.

Collapsed visibility is derived centrally in `_sync_object_states()`: descendants
and their connectors hide without overwriting each object's own `hidden` property.
Moving a frame previews all descendant graphics, then commits group and element
positions as one patch-based Undo command. Nested group frames move once and shared
descendant IDs are de-duplicated.

Reusable subflows use the JSON-only `monkez-subflow` version-1 envelope. Export
normalizes element/group coordinates relative to the root group and includes only
internal connectors. Import collision-remaps every object/member/endpoint ID,
restores nested groups in dependency order and commits the instance atomically.
No document field names a Python module or callable.

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

## Workflow execution boundary

`monkez_canva/workflow.py` is Qt-free and consumes a `CanvasDocument` projection
through `WorkflowGraph.from_document()`. Only supported `wf_*` node records and
connectors whose endpoints both belong to the workflow graph participate. Port
IDs are validated while compiling; graphics objects, timers and widget state
never enter the executor.

`WorkflowExecutor` owns a stable priority/logical-time heap. Every work item has
a token ID, payload, metadata, input port and scheduled logical time. Built-in
handlers return normalized `WorkflowNodeResult` emissions; application handlers
may be registered per node or per type. A plain mapping returned by a custom
handler remains payload data, while explicit multi-port routing uses
`WorkflowNodeResult`, avoiding ambiguous dictionaries.

The Qt adapter subscribes through one event sink. It projects node states and
trace into transient canvas dictionaries/signals and may mirror connector
emissions as `MessageTicket` animations. Visualization is optional and never
controls execution. Workflow config stays canonical JSON under the element
`workflow` property, while executor state, payloads, outputs and errors are
excluded from save/Undo. The debugger and Inspector are public-API clients, not
executor owners.

The catalog lives in `workflow_components.py` under plugin owner
`monkez.workflow`. It is opt-in to protect default palette density. Enabling it
late reconciles missing workflow placeholders without changing IDs; disabling
it unloads definitions while preserving canonical records.

## Declarative data-binding boundary

Element records may contain a `bindings` array. Each record names a stable ID,
source ID, target and JSON-only transform/timing/fallback configuration. Source
IDs are logical addresses, not network URLs or Python imports. The document never
stores QObject pointers, callables, model indexes, credentials or the last value.

`monkez_canva/data_binding.py` compiles those records into `BindingSpec` values.
`DataBindingEngine` is Qt-free and source-agnostic: hosts push source values,
logical time decides immediate/pending/stale transitions, and one batch callback
receives normalized `BindingUpdate` values. Safe transforms are an allowlist;
arbitrary expressions and `eval` are prohibited. Duplicate global binding IDs and
multiple writers to one element target are rejected before document mutation.

The widget adapter owns subscriptions. `bindSignal`, `bindQObjectProperty`,
`bindCallable`, `bindModelIndex` and `bindDataAdapter` all feed the same engine.
Callable polling, debounce/throttle flush and stale checks share one 33 ms timer;
signal-only sources allocate no timer. Disconnect callbacks are retained and run
on explicit unbind or canvas close.

Projection updates bypass `documentChanged` and graphics-to-model reconciliation.
The adapter snapshots a target's canonical presentation before the first live
value, restores it when a definition is removed, and reapplies live state after a
canonical target edit. Geometry bindings explicitly update attached/auto-routed
connectors. Port targets reuse typed-port runtime validation. Highlight/animation
are trigger targets and do not have persistent baselines.

## Native component-pack boundary

`monkez_canva/component_packs.py` is the Qt-free catalog and ownership boundary.
It publishes immutable `ComponentPack` records for `monkez.dashboard`,
`monkez.industrial` and `monkez.software`; none are part of the default registry.
Definitions contain only JSON defaults/schema, typed ports, capabilities and a
stable plugin/version identity. Documents never name renderer classes or modules.

When a host calls `enableComponentPack()`, the Qt adapter clones each definition
with shared native renderer and schema-driven Inspector factories from
`_canva_pack_renderers.py` and `_canva_pack_inspector.py`. Conflict checking is
preflighted for the whole pack. A `__missing__` placeholder is replaceable, while
an unrelated plugin owner is never silently overwritten. Disable unloads factories
but preserves canonical records; enabling later reconciles the same graphics IDs.

Pack-specific live values use `property.<schema-name>` bindings. The adapter
validates each runtime value through the registered `ElementDefinition`, stores a
transient baseline, repaints the item and restores the canonical value on unbind.
The document/Undo/autosave stream therefore never receives the live projection.

Registry defaults must be applied before generic port fallbacks. This invariant
ensures workflow and pack definitions retain their declared typed ports; fallback
`in`/`out` ports are created only for definitions that omit a port schema.

## Export and graph-exchange boundary

`monkez_canva/exchange.py` is the Qt-free selection and text-export boundary.
`select_graph()` validates requested stable IDs, expands nested groups and includes
connectors whose endpoints both belong to the selected graph. DOT and Mermaid
consume this identical resolved scope, so headless automation and the visible
editor cannot disagree about graph membership. Text escaping is format-specific;
neither exporter executes templates or invokes an external process.

DOT import uses the same module but remains a deliberately conservative parser,
not a Graphviz execution boundary. It accepts at most 5 MiB and 10,000 graph
objects, rejects subgraphs/HTML labels/mismatched edge operators, clamps geometry
and stroke values, and emits plain portable records plus warnings. Missing
positions pass through the deterministic auto-layout adapter. The Qt facade alone
resolves registry types, enables known native packs, infers endpoint ports,
performs collision-safe ID remapping and optionally creates a subflow group.
Document insertion is precomputed before one history mutation, so a failed graph
never leaves a partially imported document.

## Public component SDK boundary

`monkez_canva/sdk.py` is Qt-free and owns the public `ComponentPlugin` manifest,
SDK compatibility checks and atomic registry install/uninstall helpers. A manifest
is an explicit trusted host object; no document field is ever interpreted as a
module path or entry point. Every definition must declare the manifest's normalized
owner ID, and duplicate or foreign-owned type conflicts fail before the caller's
registry changes. Existing definitions from the same owner and safe `__missing__`
placeholders support idempotent install and in-place upgrade.

`MonkezCanva.registerElementPlugin()` is the Qt adapter. It preflights existing
records against candidate schemas, installs the complete manifest, reconciles
migrations/type factories without replacing graphics identity, rebuilds the
palette once and emits `componentPluginChanged`. Unload removes factories only;
canonical records remain portable missing components. Renderer/Inspector errors
stay isolated by the existing factory boundary and are surfaced as diagnostics.

`monkez_canva/templates.py` owns the Qt-free reusable-template boundary. A
versioned manifest wraps a validated subflow with portable catalog metadata;
5 MiB/10,000-object limits and dependency checks apply before instantiation.
`TemplateCatalog` maps normalized IDs to `.monkez_canva/templates` without path
input, sorts deterministically and isolates malformed files. The Qt facade only
adapts group export/import, signals and project-root resolution; instantiation
continues through the existing atomic Undoable subflow operation.

`monkez_widgets/_canva_export.py` is the Qt adapter for PNG, SVG, PDF and printing.
One render-state context temporarily hides excluded objects, clears selection and
smart-guide artifacts, optionally suppresses background/grid painting, then
restores all original state in `finally`. Export therefore never mutates the
document, history, runtime state or persistent project. PDF and `QPrinter` share
the public Qt-free `CanvasPageConfig`; the native Page Setup dialog only updates
that in-session value. All UI actions call the public facade methods rather than
painting or writing files independently.

## Roadmap

1. Clipboard, keyboard nudging and true mixed-value property editing.
2. Searchable palette, command palette and contextual actions.
3. Typed ports, advanced routing and group/subflow rendering.
4. Port data types, cardinality rules and auto layout.

## Deterministic auto-layout boundary

`monkez_canva/auto_layout.py` is deliberately Qt-free. `layout_graph()` accepts
normalized `LayoutNode`, `LayoutEdge` and `LayoutOptions` values and returns a
`LayoutResult`; it never reads graphics items or writes a document. This keeps
layered/tree/radial/force behavior reproducible in headless tests and allows a
future optional third-party adapter without changing the public canvas API.

`MonkezCanva.computeAutoLayout()` is the non-mutating preview boundary.
`autoLayout()` resolves scope and graph records, calls the engine, then applies
all positions and eligible group bounds through exactly one document mutation.
Locked items remain anchors. Standalone line elements and hidden records are
excluded by default, while connectors only influence layout when both endpoints
belong to the resolved scope. UI surfaces are adapters only: View card, context
menu and command palette all call the same public method.
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
