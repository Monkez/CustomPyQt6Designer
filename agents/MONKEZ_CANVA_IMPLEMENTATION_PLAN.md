# MonkezCanva implementation plan for agents

Updated: 2026-08-09
Status: active master plan
User-facing roadmap: `docs/MONKEZ_CANVA_MASTER_ROADMAP.md`

## Objective

Implement the complete MonkezCanva roadmap while preserving runtime behavior,
Qt Designer compatibility, portable persistence and version-1 documents.

## Mandatory sequencing

Do not build large component packs directly into the current monolithic module.
Complete the foundation in this order:

1. model and granular operations;
2. registry and schema-driven editor metadata;
3. command history;
4. document schema/migration/recovery;
5. shared animation scheduler;
6. editor UX, groups, typed ports and layout;
7. runtime nodes, packet debugging and data binding;
8. packs, export and SDK.

## Proposed module boundaries

```text
monkez_canva/
├── widget.py                 # public MonkezCanva facade
├── document/
│   ├── models.py
│   ├── operations.py
│   ├── schema.py
│   ├── migrations.py
│   └── persistence.py
├── registry/
│   ├── element_registry.py
│   ├── property_schema.py
│   └── builtins.py
├── graphics/
│   ├── scene.py
│   ├── view.py
│   ├── element_item.py
│   ├── connector_item.py
│   ├── handles.py
│   └── effects.py
├── editor/
│   ├── pane.py
│   ├── inspector.py
│   ├── palette.py
│   ├── layers.py
│   ├── minimap.py
│   └── commands.py
├── runtime/
│   ├── scheduler.py
│   ├── messages.py
│   ├── execution.py
│   ├── bindings.py
│   └── diagnostics.py
└── layouts/
    ├── base.py
    ├── layered.py
    └── graphviz_adapter.py
```

Keep a compatibility re-export at the existing
`monkez_widgets/monkez_canva.py` path during extraction.

## Phase completion contract

Every phase requires:

- public API and persistence compatibility analysis;
- focused tests plus the complete test suite;
- visual QA of edit mode and demo;
- updated user docs and this agent status file;
- exact staging that excludes user-owned unrelated changes;
- a scoped commit and push on the active `codex/` branch.

## Architectural constraints

- Never deserialize executable Python or import arbitrary modules from JSON.
- Registry types must be explicitly registered/allowlisted.
- Do not make graphics items the canonical document state.
- Runtime packet/message state is transient unless an explicit trace recording
  feature is enabled.
- Avoid nested event loops in new APIs; retain the current blocking API only as
  a compatibility wrapper around a future `MessageTicket`.
- One shared animation clock must replace per-item active timers.
- Commands must store minimal inverse data and support macro/compression.
- Missing assets and missing component types must degrade to placeholders.
- Auto-layout must run through an adapter and return operations; it must not
  mutate graphics items directly.

## First implementation milestone

Deliver a no-visible-regression extraction:

1. create immutable/serializable model records;
2. load version-1 JSON into the model;
3. render the existing node, splitter, line, connector and charts from models;
4. mirror existing public mutations as model operations;
5. keep the current Inspector and persistence behavior working;
6. prove JSON round-trip equality and existing 122-test compatibility.

### Progress — 2026-08-09

Delivered under `MC-CORE-MODEL-001`:

- Qt-free immutable scene, element, connector, port, group and resource records;
- version-1 loading with legacy arrow/polyline normalization;
- global ID, endpoint, port and finite-JSON validation;
- atomic revisions, granular operation events, rename and cascade removal;
- `MonkezCanva.setDocumentModel()` and synchronized multi-view rendering;
- independent model tests plus full-suite regression coverage (130 passing);
- incremental operation rendering for scene, element and connector records;
- stable graphics identity, selection and viewport across external revisions;
- model-first public add/update/remove/rename/connect operations;
- complete connector/group/resource update, rename and removal lifecycle APIs.

Phase 1.1 is complete. Follow-up work moves to the registry and command layers:

- generate element defaults and validation from registry metadata rather than
  duplicated renderer-side normalization;
- route remaining direct gestures/compound editor actions through commands;
- add group/resource graphics after their renderer registrations exist.

### Registry progress — 2026-08-09

Phase 1.2 now provides public `ElementDefinition` and
`ElementRegistry` APIs, isolated per canvas through a cloneable built-in catalog.
The Elements pane, add defaults and custom component categories read registry
metadata. Unknown project component types render as explicit safe placeholders.
Definitions now include validated JSON-schema rules, component versions,
contiguous migrations, capability-driven standard Inspector sections, optional
renderer/Inspector factories and plugin ownership/version metadata. Plugin unload
preserves records; late registration restores missing components in place.

Phase 1.2 acceptance is complete. The next core milestone is Phase 1.3:
command-based history with minimal inverse operations, macros and compression.

### Command history progress — 2026-08-09

Phase 1.3 is complete. Whole-document history snapshots were removed in favor of
an 80-entry `QUndoStack`. Commands store minimal record patches, preserve record
order, restore cascade changes atomically and use specialized rename operations
to preserve graphics identity. Model-first mutations and graphics-origin edits
share the stack; updates merge for 800 ms and multi-object actions use macros.
The public API exposes stack/state/text, macro boundaries and group/resource
commands. Save/load/session boundaries maintain an explicit clean/dirty state.

### Schema and recovery progress — 2026-08-09

Phase 1.4 is complete. `schema.py` publishes the version-1 Draft 2020-12 JSON
Schema, structural validation and the ordered document-migration boundary.
`persistence.py` performs same-directory atomic replacement, retains the last
valid primary as `.bak`, recovers corrupt/missing primary files without silently
overwriting them, and maintains SHA-256/size manifests for every managed asset.
Both ordinary path loading and portable persistence report recovery and integrity
diagnostics. Documents or registered components newer than the runtime render in
an explicit read-only compatibility mode; mutation, autosave and durable save are
blocked while Layers, viewport navigation, highlighting and runtime signals remain
available. The Floating Cards pane and quick toolbar expose that state.

### Shared animation progress â€” 2026-08-09

Phase 1.5 is complete. `_canva_animation.py` provides one weak-reference,
visibility-aware scheduler for line/connector effects, packet transport and
runtime property tweens. It culls repaint requests to the visible scene, pauses
nonessential hidden work and preserves completion of explicitly sent packets.
`animationStats()` and the clamped frame-interval API provide diagnostics.

Next: Phase 2 professional editor UX, beginning with clipboard, keyboard nudge
and mixed-value multi-selection Inspector behavior.

### Editor UX progress — 2026-08-09

`MC-EDITOR-SELECTION-001` completes the first Phase 2 slice. The Qt-free
clipboard module validates and remaps portable subgraphs; canvas APIs and
Ctrl+C/X/V preserve internal connectors and commit cut/paste/duplicate atomically.
Arrow shortcuts support exact 1/10/0.1-pixel nudging with compressed history.
The Inspector renders persistent `Mixed` states for common multi-selection
properties and applies only explicitly edited fields in one macro command.

Next: searchable palette/favorites/recent items and a context-aware command
palette, followed by smart guides and configurable snap targets.

### Palette and command discovery progress — 2026-08-09

`MC-EDITOR-PALETTE-001` adds the Qt-free palette search/ranking layer, dynamic
two-column component tiles, category/Favorites/Recent filters and portable scene
preferences. Recent updates share the Add command. `MC-EDITOR-COMMAND-001` adds
the Ctrl+K launcher with live context from registry, selection, clipboard,
history and read-only state plus full arrow/Enter/Escape keyboard operation.

Next: context-aware blank/item/connector menus, equal-size actions, smart guides
and configurable grid/edge/center/port snapping.

### Direct manipulation progress — 2026-08-09

`MC-EDITOR-SNAP-001` adds a Qt-free deterministic snapping engine and portable
scene preferences for target set, threshold and smart-guide visibility. Direct
drag now resolves grid, edge, center and port candidates and paints transient
foreground guides. `MC-EDITOR-CONTEXT-001` adds blank/item/connector menus without
breaking right-button viewport pan, plus atomic match-width/height/both commands.
The View tab is scroll-safe and uses compact icon navigation controls.

Next: minimap, document outline, viewport bookmarks, lock/hide/isolate and
editable connector waypoint handles.

### Scene navigation progress — 2026-08-09

`MC-EDITOR-OUTLINE-001` upgrades Layers into a searchable document outline with
state icons and compact lock/hide/isolate/show/zoom actions. Lock and hidden are
portable element/connector properties committed atomically; isolate remains a
non-destructive view filter. `MC-EDITOR-MINIMAP-001` adds a floating interactive
overview plus portable center/zoom bookmarks and View-tab controls.

Completed: editable connector waypoints, rounded orthogonal corners, reroute
handles, edge labels, parallel-edge separation and crossing bridges.

### Advanced routing progress — 2026-08-09

`MC-EDITOR-ROUTING-001` adds Qt-free orthogonal/lane helpers, rounded paths,
self-loops, stable parallel-edge separation and shared edge labels. Selected
connectors expose draggable waypoint handles; add/move/remove/clear APIs and
Inspector/context/command actions all commit canonical records through Undo.

`MC-EDITOR-ROUTING-002` adds deterministic obstacle-aware Manhattan routing,
proper crossing detection with cached bridge rendering and semantic bus styles
(`trunk`, `double`, width and ID). Inspector, context actions and public APIs use
the same canonical connector fields and remain undoable.

`MC-EDITOR-GROUP-001` adds canonical frame/swimlane/subflow projection, nested
cycle validation, collapse-derived visibility, group movement, object-specific
Inspector/context/command actions and Layers/Minimap integration. Portable
`monkez-subflow` templates export relative coordinates and atomically import with
collision-safe ID, member, endpoint and waypoint remapping.

### Typed graph progress — 2026-08-09

`MC-RUNTIME-TYPED-PORTS-001` adds `typed_ports.py` as the Qt-free source of truth
for canonical port records, direction, cardinality, type/unit conversion and
runtime value diagnostics. Document operations roll invalid element-port edits
back; code, reconnect and direct manipulation consume the same result. The
Inspector exposes the full contract with immediate updates and visual drag QA
distinguishes direct, converted and rejected targets. Runtime values remain
transient and are cleaned up on rename/removal/clear.

### Auto-layout progress â€” 2026-08-09

`MC-EDITOR-LAYOUT-001` adds `auto_layout.py` as a Qt-free deterministic boundary.
It consumes immutable node/edge geometry and returns top-left positions plus
metrics without mutating the document. Layered layout condenses cycles through
SCCs and applies stable barycentric sweeps; tree layout reserves subtree extents;
radial layout uses graph distance; force layout uses deterministic relaxation and
collision passes. The widget adapter resolves smart document, selection,
connected-component or group scope, preserves locked nodes, fits eligible groups
and commits all changed geometry through one history command.

Packet runtime v2/debugging is implemented in the following milestone; workflow
execution follows it.

### Packet runtime v2 foundation — 2026-08-09

`MC-RUNTIME-PACKET-001` adds a Qt-free packet lifecycle boundary in
`packet_runtime.py`. `MessageTicket` carries transient payload, metadata, priority,
TTL, timeout, branch policy, status, pending count, route and failure details.
`PacketRuntime` validates transitions, retains a bounded ordered trace, supports
breakpoints and deterministically selects splitter branches. The Qt adapter owns
only graphics packets and deferred breakpoint arrivals; pause/step/resume/cancel
operate through public canvas APIs. A separate Tool-window debugger subscribes to
ticket/trace signals and can be replaced by host UI without coupling to internals.

The 1,000-concurrent-ticket headless scenario is part of the unit suite. Next:
workflow component definitions/executor, replay, aggregate link metrics and
failure-edge routing.

### Workflow execution progress — 2026-08-09

`MC-RUNTIME-WORKFLOW-001` implements the Qt-free graph compiler/executor and the
29-component opt-in Workflow Pack. Declarative routing, timing and logic nodes,
custom handler boundaries, logical-time stepping, trace and cycle guards are
covered headlessly. `MonkezCanva` exposes lifecycle APIs/signals, transient node
badges, packet visualization, context/command actions, a conditional Inspector
card and the Workflow tab in Runtime Debugger. The demo enables the pack and
runs a Source → Transform → Sink example.

Next runtime slices: recurring timer scheduling, bounded queue/backpressure,
replay fixtures, link metrics and explicit workflow failure-edge conventions.

### Declarative data-binding progress — 2026-08-09

`MC-RUNTIME-BINDING-001` adds the Qt-free `data_binding.py` evaluator and the
element-local `bindings` schema. It implements safe transforms/formatting,
logical-time debounce/throttle/stale transitions, stale/error fallback, bounded
trace and batched target delivery. The canvas owns transient baselines, runtime
projection, one shared scheduling timer and adapters for Qt signals/properties,
callables, model indexes and conventional external QObject adapters. Inspector,
context/command discovery, Runtime Debugger, demo and public APIs use the same
definitions and state.

Next data slices: optional MQTT/WebSocket/OPC-UA/Modbus adapter packages,
historian/ring-buffer policies, write-back bindings and aggregate source health.

### Native component-pack progress — 2026-08-09

`MC-PACK-NATIVE-001` completes Phase 4 with 43 opt-in components across Dashboard,
Industrial and Software/Flowchart. `component_packs.py` owns immutable Qt-free
catalogs; separate Qt modules own vector painting and compact schema-generated
property controls. Canvas APIs, palette, blank context menu and Ctrl+K can enable
or disable each pack without mutating its document. Typed ports, missing-component
reconciliation and validated `property.<schema-name>` data bindings are covered.

Next ecosystem slices: PNG/SVG/PDF export, page/print configuration, DOT/Mermaid
exchange, public SDK/example plugin and document diagnostics/diff.

### Export and graph-exchange progress — 2026-08-09

`MC-ECOSYSTEM-EXPORT-001` completes scene/selection PNG, transparent PNG, SVG and
PDF export through one native Qt render pipeline. Editor-only state is suppressed
and restored transactionally. Public page configuration, native Page Setup,
Print Preview, floatbar/context/Ctrl+K discovery and `exportCompleted` diagnostics
share the same API. The Qt-free `exchange.py` layer adds nested-scope resolution,
deterministic DOT output and constrained Mermaid flowcharts with safe escaping.

`MC-ECOSYSTEM-EXCHANGE-002` completes constrained DOT import and import-as-subflow.
The Qt-free parser bounds input, rejects executable/complex Graphviz constructs,
restores exported semantics and deterministically lays out missing positions. The
widget adapter remaps collisions, resolves known packs, infers endpoint ports and
commits the imported graph through one Undo command.

`MC-ECOSYSTEM-SDK-003` publishes a Qt-free, versioned component manifest and
atomic registry installer. The canvas adapter preflights existing records,
reconciles placeholders without changing graphics identity and reports plugin
lifecycle. A trusted Telemetry example covers renderer, typed port and auto-apply
Inspector contracts in the real demo.

`MC-ECOSYSTEM-TEMPLATE-004` provides the reusable project-template foundation:
bounded manifests, deterministic `.monkez_canva/templates` catalog, searchable
metadata and collision-safe/Undoable canvas publishing and instantiation APIs.

`MC-ECOSYSTEM-TEMPLATE-005` completes the visual template slice with a detached
search/tag browser, safe PNG thumbnail capture and fallback previews. Context,
Ctrl+K and public APIs share one instantiation path.

Next: document diff/diagnostics reports and plugin packaging/discovery policy.

`MC-EDITOR-PANE-005` removes the remaining Windows native spin-button artifacts
with owned borderless steppers. It also refines the five-tab segmented bar,
selected icon color, field focus states, card title clearance and JSON editor
styling. Visual QA targets the full 438×720 pane and Position / size card.

## Backlog tracking

Use stable IDs `MC-PHASE-TOPIC-NNN`, for example:

- `MC-CORE-MODEL-001`
- `MC-CORE-REGISTRY-001`
- `MC-EDITOR-MINIMAP-001`
- `MC-RUNTIME-PACKET-001`
- `MC-PACK-INDUSTRIAL-001`

Record design decisions in `agents/MONKEZ_CANVA_ARCHITECTURE.md` and user-visible
milestones in `agents/STATUS.md` immediately after changes.

## Current user-owned files to preserve

At plan creation, `examples/splash_screen.ui` is modified and `.monkez_canva/`
is untracked. They are unrelated user work. Do not stage, reset, move or delete
them unless the user explicitly changes their scope.
