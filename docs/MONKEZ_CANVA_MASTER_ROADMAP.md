# MonkezCanva master roadmap

Updated: 2026-08-09

## Product target

MonkezCanva will evolve from a runtime canvas widget into a reusable native
PyQt6 visual workspace for diagrams, dashboards, workflow editing, simulation
and live application interaction. It must remain usable from Qt Designer,
portable with a copied project, code-addressable by stable IDs and independent
of WebEngine.

## Delivery principles

- Strengthen the extension architecture before adding large component packs.
- Keep every saved document JSON-only, validated and migratable.
- Preserve old `arrow`, `polyline` and version-1 document compatibility.
- Keep edit mode optional; runtime applications must stay lightweight.
- Make every visible editor mutation undoable and autosave-safe.
- Benchmark large scenes and packet animation before claiming scalability.
- Ship each phase with docs, demo coverage, automated tests and visual QA.

## Phase 1 — Core platform

### 1.1 Independent document model

Introduce `CanvasDocument`, `SceneModel`, `ElementModel`, `ConnectorModel`,
`PortModel`, `GroupModel` and resource records. Graphics items observe models;
they are no longer the source of truth.

Acceptance:

- document operations can be unit-tested without constructing a visible window;
- one document may be rendered by more than one view;
- model changes emit granular change records;
- loading version-1 projects produces the same visible graph.

Completed (2026-08-09): Qt-free records, validation, revisioned operation events,
version-1 normalization, shared multi-view attachment and incremental operation
rendering are implemented. Public element/connector add, update, remove, rename
and connect APIs are model-first. External updates retain graphics identity,
selection and viewport. The compatibility reconcile path remains only for direct
graphics gestures and compound actions until command-based history lands.

### 1.2 Public element registry

Each element type registers its model defaults, JSON schema, renderer, Inspector
factory, category, icon, migrations and optional runtime handler. The Add pane
and Inspector must be generated from registry metadata.

Acceptance:

- a third-party element can be registered without editing `monkez_canva.py`;
- an unknown element loads as a safe missing-component placeholder;
- duplicate type IDs and invalid schemas fail with actionable diagnostics.

Completed (2026-08-09): public ordered/cloneable definitions, built-in schemas,
metadata-driven Add pane/default sizes, custom registration and safe missing-type
placeholders are implemented. Definitions support validated schemas, versioned
migrations, capability-driven Inspector sections, renderer/Inspector factories
and plugin ownership. Factory errors degrade safely and plugin unload keeps data.

### 1.3 Command-based history

Replace whole-document history snapshots with `QUndoStack` commands for add,
delete, move, resize, property change, port change, grouping and connection.
Continuous drags and typing are compressed; multi-object actions use macros.

Completed (2026-08-09): the editor uses `QUndoStack` with minimal scene/record
patches, explicit identity-preserving rename commands, an 80-command bound,
800 ms update compression and macros for multi-object delete/clear plus public
macro APIs. Add/delete/move/resize/property/port/group/resource/connection edits
are reversible. Undo/Redo labels, enabled state, shortcuts and dirty/clean save
state are exposed to the pane and floating toolbar.

### 1.4 Schema, migrations and recovery

Add JSON Schema, versioned migrations, atomic writes, recovery backup, asset
checksums and read-only handling for documents newer than the runtime.

Completed (2026-08-09): the public Draft 2020-12 schema and migration boundary
are Qt-free. JSON saves use atomic same-directory replacement and preserve the
last valid primary in `.bak`; corrupt or missing primary files recover with an
explicit signal/diagnostic. Portable media, packet icons, backgrounds and resource
URIs receive SHA-256/size manifest entries and integrity verification. Newer
document/component schemas open visibly in read-only mode and cannot be modified,
autosaved or overwritten by the older runtime.

### 1.5 Shared animation scheduler

Move line, packet and runtime animation to one canvas-level clock. Update only
visible dirty regions and pause nonessential effects when the view is hidden.

Completed (2026-08-09): one visibility-aware clock now advances standalone line
effects, connector effects, packet transport and `animateElement()` tweens.
Visible-scene culling bounds repaint work; hidden decorative animation and loops
pause, while explicitly sent packets still finish and release blocking callers.
Runtime metrics and a configurable frame interval support profiling.

### 1.6 Large-scene rendering and measurable performance

Completed (2026-08-09): `MC-CORE-PERFORMANCE-002` adds a Qt-free render policy
with Full, Compact and Overview tiers. Auto mode resolves a tier from zoom,
selection and 1,000/10,000-object pressure; Quality and Speed are explicit
overrides. Elements, groups and connectors omit labels, ports, plugin internals,
crossing bridges and decorative effects only when their profile allows it.
Selected objects retain detail in Auto, active packets remain visible at every
tier and export forces transactional full-quality rendering.

Document attachment now batches graphics creation, visibility reconciliation,
parallel-edge updates and notifications instead of doing global work per item.
The public frame tracker reports bounded average/p95/max paint time, visible paint
counts and tier counts. `benchmark_canva.bat` produces a machine-readable baseline
for 100, 1,000 and 10,000 real `QGraphicsItem` nodes. The first committed Windows
baseline is stored under `docs/benchmarks/`.

## Phase 2 — Professional editor UX

Completed slice (2026-08-09): versioned graph clipboard with internal-connector
preservation and collision-safe ID/endpoint remapping; atomic cut/paste/duplicate;
1/10/0.1-pixel keyboard nudge with compressed undo; and a true mixed-value
multi-selection Inspector for common geometry, content and appearance controls.

Completed slice (2026-08-09): registry-driven component search, category filters,
portable favorites/recent history and a keyboard-first Ctrl+K command launcher.
Commands are rebuilt from current selection, clipboard, history, registry and
read-only state each time the launcher opens.

Completed slice (2026-08-09): context-aware blank/item/connector menus while
preserving right-drag viewport pan; equal width/height/both actions; portable
grid/edge/center/port snap settings; and foreground smart alignment guides.

Completed slice (2026-08-09): floating interactive minimap, searchable document
outline, portable viewport bookmarks, document-backed lock/hide state and
non-destructive viewport isolation. All state-changing actions use Undo/Redo.

Completed slice (2026-08-09): draggable waypoint handles, rounded orthogonal
routes, self-loops, edge labels and stable automatic separation of parallel
connectors. Routing parameters are portable, undoable and Inspector-editable.

- searchable palette with categories, favorites and recent items — complete;
- command palette and context-aware canvas menus — complete;
- copy, cut, paste and duplicate with internal connector preservation — complete;
- keyboard nudge, equal-size actions and smart alignment guides — complete;
- configurable snap targets: grid, center, edge and port — complete;
- mixed-value multi-selection Inspector — common-property slice complete;
- minimap, document outline, viewport bookmarks and zoom-to-selection — complete;
- lock, hide and isolate item/group — complete;
- editable connector waypoints, rounded orthogonal corners and reroute points — complete;
- edge labels, self-loops, parallel edges, crossing bridges and visual buses — complete;
- obstacle-aware Manhattan routing with configurable clearance — complete;
- group/frame, swimlane, nested/collapsible group and reusable JSON subflow — complete;
- automatic layout adapter with layered, tree, force and radial strategies — complete.

Completed (2026-08-09): `MC-EDITOR-LAYOUT-001` adds a deterministic Qt-free
layout engine with cycle-safe SCC layering, subtree-aware trees, graph-distance
radial rings and seeded force simulation. Smart document/selection/component/group
scope, locked-node preservation, disconnected-component packing, optional group
fitting and one-command Undo are available through the View pane, context menu,
Ctrl+K commands and public Python API.

## Phase 3 — Typed graph and workflow runtime

### Typed ports

Ports gain data type, unit, optional/required, default value, connection count,
accepted conversions, tooltip and runtime value. Compatible targets highlight
during connection; invalid targets explain the reason.

Completed (2026-08-09): `MC-RUNTIME-TYPED-PORTS-001` adds the Qt-free canonical
port normalizer and compatibility/value validators; mode orientation, cardinality,
type/unit conversion and detailed reasons are enforced by `CanvasDocument`, code
APIs, reconnect and drag gestures. The node Inspector edits the complete contract
with immediate updates. Green/purple/red port halos and preview colors distinguish
direct, converted and rejected targets. Runtime values/signals stay view-local and
never enter portable JSON. The public v1 schema now documents the port contract.

### Runtime components

- routing: Junction, Reroute, Merge, Splitter, Switch, Router, Multiplexer,
  Demultiplexer and Bus;
- timing: Timer, Delay, Queue, Buffer, Throttle, Debounce, Retry and RateLimiter;
- logic: Gate, Compare, Filter, Transform, Map, Counter and StateMachine;
- boundaries: Source, Sink, InputInterface, OutputInterface and ErrorHandler.

Completed foundation (2026-08-09): `MC-RUNTIME-WORKFLOW-001` ships all 29 types
as the opt-in `monkez.workflow` registry pack. A Qt-free deterministic executor
compiles the portable document, routes typed-port emissions with logical time,
supports declarative transform/filter/switch/timing/state operations and exposes
node/type custom-handler boundaries. Canvas integration adds run/step/pause/
resume/cancel APIs, transient node status, packet visualization, signals, an
  object-specific Inspector card and a Workflow debugger timeline.

Completed slice (2026-08-09): `MC-RUNTIME-WORKFLOW-002` adds bounded executor and
per-Queue-node backpressure with deterministic reject/drop policies, recurring
logical schedules with finite/unlimited occurrence limits and all/latest/skip
catch-up, pause/resume/cancel controls, portable failure envelopes on `error` or
`failure` edges, and an optional Qt wall-clock adapter. Runtime Debugger exposes
queue pressure, schedule state and deterministic +1 second stepping; all runtime
state remains transient.

### Packet runtime v2

Add `MessageTicket`, non-blocking and async APIs, payload metadata, priority, TTL,
timeouts, cancellation, trace, failures, replay, bandwidth/latency metrics and
branch policies. Provide pause, resume, step, breakpoint and packet Inspector.

Completed foundation (2026-08-09): `MC-RUNTIME-PACKET-001` introduces the Qt-free
`PacketRuntime`, live `MessageTicket`, bounded ordered trace and deterministic
`all`/`first`/`round_robin` branch policies. Canvas APIs cover non-blocking and
async waits, payload/metadata, priority, hop TTL, timeout, cancellation, pause,
resume, single-step and object breakpoints. A detached debugger provides message
and timeline views without persisting runtime state. Replay, bandwidth/latency
aggregation and explicit failure-edge routing remain for the workflow executor
milestone.

### Data binding

Bind element properties to Qt signals/properties, callables, model indexes and
optional adapter sources such as MQTT, WebSocket, OPC-UA or Modbus. Support
transform, format, debounce, throttle, stale state, error fallback and batched
painting.

Completed foundation (2026-08-09): `MC-RUNTIME-BINDING-001` adds a Qt-free,
source-agnostic engine with safe declarative transforms, formatting, deterministic
debounce/throttle/stale behavior, stale/error fallbacks and batch delivery. Binding
definitions are element-local portable JSON; live values/subscriptions never dirty
the document. Canvas adapters cover push feeds, Qt signals/properties, callables,
model indexes and conventional external adapters through one shared timer. Text,
chart, appearance, geometry, port, highlight and animation targets are supported,
with an object-specific Inspector and Runtime Debugger tab. Protocol-specific
connectors, historian windows and write-back remain optional ecosystem adapters.

## Phase 4 — Component packs

### Dashboard

KPI card, sparkline, gauge, progress ring, pie/donut, scatter, area, histogram,
heatmap, timeline, event log, data table, status light and alarm banner.

### Industrial

Tank, pump, valve, motor, fan, pipe, sensor, PLC, circuit breaker, battery,
transformer and conveyor.

### Software and flowchart

Database, server, cloud, API, queue, topic, cache, file, service, container,
process, decision, document, terminator, annotation and sticky note.

Packs are registry packages; they must not enlarge the default palette until
enabled by the application.

Completed (2026-08-09): `MC-PACK-NATIVE-001` ships all 43 planned components as
three opt-in Qt-free catalogs. The Qt adapter attaches native vector renderers,
schema-driven compact Inspectors and typed ports only when a pack is enabled.
Palette, blank-canvas menu, Ctrl+K and public APIs share the same enable/disable
state. Pack records remain portable and recover from missing-component placeholders.
Declarative binding now supports validated `property.<schema-name>` targets so
live values drive pack-specific properties without persisting runtime state.

## Phase 5 — Export and ecosystem

- PNG, transparent PNG, SVG and PDF export for scene or selection;
- print preview and page configuration;
- DOT import/export and a constrained Mermaid exporter;
- reusable templates and import-as-subflow;
- public component SDK and example plugin;
- document diff and diagnostics report;
- collaboration only after operation IDs and conflict semantics are stable.

Completed slice (2026-08-09): `MC-ECOSYSTEM-EXPORT-001` adds one native export
pipeline for scene/selection PNG, transparent PNG, SVG and PDF. It suppresses
editor artifacts, restores visibility/selection transactionally and shares a
validated A3/A4/A5/Letter/Legal page configuration with native Page Setup and
Print Preview. Qt-free deterministic DOT and constrained Mermaid exporters keep
stable IDs, labels, component shapes, ports, arrow direction and nested-selection
semantics. Floatbar, context menus, Ctrl+K, public APIs and demo diagnostics use
the same implementation.

Completed slice (2026-08-09): `MC-ECOSYSTEM-EXCHANGE-002` adds a constrained,
Qt-free DOT importer with bounded input/object sizes, deterministic fallback
layout and actionable parser errors. The canvas adapter remaps colliding IDs,
restores endpoint ports and known component packs, degrades unknown types safely,
places the graph at a requested point or viewport center and can wrap it as one
reusable subflow. Each successful import is one Undo command and is available
through the blank-canvas menu, Ctrl+K, public API and demo diagnostics.

Completed slice (2026-08-09): `MC-ECOSYSTEM-SDK-003` publishes a Qt-free
component-plugin manifest and atomic registry installer with SDK compatibility,
ownership, duplicate and conflict validation. The canvas facade reconciles
missing-component records in place, exposes lifecycle signals and keeps unload
document-safe. A complete trusted Telemetry plugin demonstrates vector painting,
typed ports and an auto-apply Inspector in the diagnostic demo.

Completed foundation (2026-08-09): `MC-ECOSYSTEM-TEMPLATE-004` adds a bounded,
Qt-free reusable-template manifest and deterministic project-local catalog under
`.monkez_canva/templates`. Canvas APIs publish groups with searchable metadata
and instantiate them through the existing collision-safe, one-command subflow
path. Malformed catalog entries are isolated with diagnostics.

Completed slice (2026-08-09): `MC-ECOSYSTEM-TEMPLATE-005` adds a detached,
searchable Template Browser with tag filtering, safe thumbnail lookup, generated
fallback previews and one-click Undoable insertion. Project templates can capture
their own PNG preview transactionally; blank-canvas context and Ctrl+K expose the
same browser without making the main Control Pane denser.

Completed slice (2026-08-09): `MC-ECOSYSTEM-DIAGNOSTICS-006` adds a Qt-free,
structured document health engine and stable ID-based semantic diff. A detached
Document Health window exposes registry/schema/version, group/resource and saved
asset-integrity findings, canvas metrics and changes since the clean save/load
baseline. Reports are exportable JSON and discoverable from blank context or
Ctrl+K without mutating history.

Completed slice (2026-08-09): `MC-ECOSYSTEM-PLUGIN-007` adds bounded project
plugin packages, deterministic non-executing discovery, whole-package SHA-256
fingerprints and a session-only exact trust store. The detached Plugin Manager
requires an explicit Trust and load action, reports invalid/conflicting packages
without stopping discovery and preserves records as missing placeholders on
unload. A standalone portable package example documents the complete contract.

## Cross-phase quality gates

- compatibility and migration tests for every document version;
- performance scenarios at 100, 1,000 and 10,000 nodes â€” complete baseline;
- packet scenarios at 10, 100 and 1,000 concurrent messages;
- keyboard-only editor paths and high-DPI visual checks;
- no timers, movies or resources left active after object deletion;
- project-local assets remain loadable after moving the repository;
- release notes and `canva_demo.bat` updated at every user-visible milestone.

## Recommended execution order

1. Document model and operation events.
2. Registry and missing-component placeholder.
3. Command history and migrations.
4. Shared scheduler and performance baseline.
5. Clipboard, search palette, minimap and smart guides.
6. Groups/subflows and typed ports.
7. Connector editing and auto-layout.
8. Workflow components and runtime execution.
9. Packet debugging and data binding.
10. Component packs, export and plugin SDK.

## Control Pane concept evaluation

Five simplified visual concepts are stored under
`docs/assets/monkez-canva-control-pane-concepts/`:

1. `01-light-essential.png` — simple general-purpose floating Inspector;
2. `02-dark-compact.png` — compact dark node/port treatment;
3. `03-floating-cards.png` — focused multi-selection actions and properties;
4. `04-slim-dock.png` — very narrow line/connector Inspector;
5. `05-progressive-inspector.png` — object-specific progressive disclosure.

They were evaluated using:

- information density without visual crowding;
- discoverability for first-time users;
- speed for expert keyboard/mouse users;
- feasibility with native PyQt6 widgets and QSS;
- light/dark and high-DPI adaptability;
- handling of long IDs, translated labels and narrow screens;
- clear separation of editing, runtime and debugging controls.

### Selected direction

Implement a simple responsive hybrid instead of copying one concept literally:

- Option 1 supplies the common shell and light visual language.
- Option 5 supplies progressive disclosure: only the primary action and 4–8
  common properties are open for the selected object type.
- Option 3's quick action card appears only for multi-selection.
- Option 4 supplies narrow line/connector rows and an optional live preview.
- Option 2 supplies the dark theme and compact typed-port summary.
- Outline, Runtime and Debugger stay in separate detachable tools rather than
  increasing the everyday Inspector's density.

Detailed images, strengths and trade-offs are recorded in the concept
[`README.md`](assets/monkez-canva-control-pane-concepts/README.md).
