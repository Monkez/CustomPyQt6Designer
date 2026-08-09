# MonkezCanva implementation plan for agents

Updated: 2026-08-08
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
