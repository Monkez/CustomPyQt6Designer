# MonkezCanva master roadmap

Updated: 2026-08-08

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

## Phase 2 — Professional editor UX

Completed slice (2026-08-09): versioned graph clipboard with internal-connector
preservation and collision-safe ID/endpoint remapping; atomic cut/paste/duplicate;
1/10/0.1-pixel keyboard nudge with compressed undo; and a true mixed-value
multi-selection Inspector for common geometry, content and appearance controls.

- searchable palette with categories, favorites and recent items;
- command palette and context-aware menus;
- copy, cut, paste and duplicate with internal connector preservation — complete;
- keyboard nudge — complete; equal-size and smart alignment guides remain;
- configurable snap targets: grid, center, edge, port and nearby object;
- mixed-value multi-selection Inspector — common-property slice complete;
- minimap, document outline, viewport bookmarks and zoom-to-selection;
- lock, hide and isolate item/group;
- editable connector waypoints, rounded orthogonal corners and reroute points;
- edge labels, self-loops, parallel edges, crossing bridges and buses;
- group/frame, swimlane, collapsible group and reusable subflow;
- automatic layout adapter with layered, tree, force and radial strategies.

## Phase 3 — Typed graph and workflow runtime

### Typed ports

Ports gain data type, unit, optional/required, default value, connection count,
accepted conversions, tooltip and runtime value. Compatible targets highlight
during connection; invalid targets explain the reason.

### Runtime components

- routing: Junction, Reroute, Merge, Splitter, Switch, Router, Multiplexer,
  Demultiplexer and Bus;
- timing: Timer, Delay, Queue, Buffer, Throttle, Debounce, Retry and RateLimiter;
- logic: Gate, Compare, Filter, Transform, Map, Counter and StateMachine;
- boundaries: Source, Sink, InputInterface, OutputInterface and ErrorHandler.

### Packet runtime v2

Add `MessageTicket`, non-blocking and async APIs, payload metadata, priority, TTL,
timeouts, cancellation, trace, failures, replay, bandwidth/latency metrics and
branch policies. Provide pause, resume, step, breakpoint and packet Inspector.

### Data binding

Bind element properties to Qt signals/properties, callables, model indexes and
optional adapter sources such as MQTT, WebSocket, OPC-UA or Modbus. Support
transform, format, debounce, throttle, stale state, error fallback and batched
painting.

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

## Phase 5 — Export and ecosystem

- PNG, transparent PNG, SVG and PDF export for scene or selection;
- print preview and page configuration;
- DOT import/export and a constrained Mermaid exporter;
- reusable templates and import-as-subflow;
- public component SDK and example plugin;
- document diff and diagnostics report;
- collaboration only after operation IDs and conflict semantics are stable.

## Cross-phase quality gates

- compatibility and migration tests for every document version;
- performance scenarios at 100, 1,000 and 10,000 nodes;
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
