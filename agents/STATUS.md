# Current engineering status

Updated: 2026-08-09

## Current version

- Working version: 0.5.0 (package rename and convenient UI loader).
- Python runtime requires Python 3.10 or newer.
- Designer development and portable build require Python 3.11.

## Supported surface

- 36 public runtime widgets/components.
- 35 Qt Designer plugins; runtime-only `MonkezToast` is intentionally excluded.
- Six themes: Material, iOS, Fluent, Bootstrap, Minimal and Dark.
- Canonical distribution/import names are `monkez-pyqt6` and `monkez_pyqt6`;
  `custom_pyqt6_designer` remains as a compatibility namespace and launcher.
- Runtime loading through `monkez_pyqt6.load_ui()`, direct
  `PyQt6.uic.loadUi()` and generated `pyuic6` code.
- `load_ui()`, `load_ui_into()` and `UiLoaderMixin` cover new top-level forms,
  existing `QMainWindow`/`QWidget` instances and parented reusable child forms.
- Optional OpenCV camera support.
- Splash screen widget/controller with Designer customization, transparent PNG
  backgrounds, progress updates and animation; see
  `agents/SPLASHSCREEN_DESIGN.md`.
- Startup-only duplicate launch protection that releases when initialization
  completes, allowing intentional additional instances afterward.
- Module-based launcher and actionable `--doctor` diagnostics.
- No-admin per-user Designer installer with Desktop/Start Menu shortcuts and
  guarded uninstall.
- Portable release onboarding files at the archive root.
- Splash Designer plugin hidden from the drag-and-drop Widget Box while
  remaining available to render standalone splash forms.
- Packaged splash template with source, portable and installed one-click
  creation workflows.
- `MonkezComboBox` honors the inherited Designer `font` property for both its
  closed control and custom popup items, including large-font row sizing.
- New `MonkezComboBox` instances contain no placeholder items; Designer forms
  and runtime code add only the application-specific choices they need.
- Custom-painted borders now share DPI-aware inset and corner-radius geometry.
  The rule covers combo popups, group boxes, radios, switches, pagination,
  calendar cells, table frames/badges, range-slider handles and dial handles,
  preventing clipped or uneven antialiasing at widget edges.
- `MonkezStatusBadge` now paints its translucent rounded surface itself and
  clamps the effective radius to live geometry. All six themes retain clean,
  transparent corners instead of relying on inconsistent Qt stylesheet clipping.
- Gallery's color-format selector now uses `MonkezComboBox` instead of a native
  combo, so its right edge, chevron and rounded frame form one coherent control.
- `MonkezImage` renders directly in its outer widget without a fixed-style
  child frame, so Designer stylesheets can control its visible background,
  border and radius.
- `MonkezImage.backgroundColor` is also applied to its transparent content
  surface, so an inherited parent stylesheet cannot replace the Designer
  property. A background declared directly on the widget stylesheet still wins.
- `MonkezImage.scaleModeIndex` is a stable Designer property with task-menu
  choices for Fit, Fill, Stretch and Original; every mode recalculates against
  the outer container size.
- `MonkezImage.set_image()` and its `setImage()`/`setFrame()` aliases accept
  detached `uint8` NumPy frames in grayscale, BGR/BGRA or RGB/RGBA formats,
  plus `str`, `bytes` and `pathlib.Path` file paths. NumPy remains lazy-loaded.
- Outlined `MonkezButton` uses `activeColor` for its border and `textColor` for
  normal text, while preserving `hoverTextColor` for hover/pressed feedback.
- Theme-derived button text is mode-aware: Filled uses `on_primary`, while
  Outlined/Text use `primary` (or `danger` when inactive), preventing the white
  text on white surface previously visible in Gallery. Explicit text and hover
  colors survive button-type changes.
- `MonkezButton` now owns Standard/Icon-only presentation and guarded loading
  state through `styleIndex`, `iconText`, `buttonSize`, `loading`, `loadingText`
  and `disableWhileLoading`. Separate Loading/Icon button entries were removed
  from Designer and Gallery; compatibility aliases remain module-local only.
- `MonkezImage` uses Ignored horizontal/vertical size policies and a zero
  minimum hint, so its outer layout owns widget geometry before the selected
  scale mode transforms the pixmap.
- `MonkezScrollArea` preserves the stock `QScrollArea` API/default policies and
  adds `autoContentSize`: child geometry and layout minimums automatically drive
  AsNeeded scrollbar visibility. Its Designer XML uses Qt's native
  `scrollAreaWidgetContents` structure and explicitly selects both AsNeeded
  policies without a custom fixed-page extension.
- Designer plugins are grouped into nine numbered workflow groups: actions,
  text/file inputs, numeric/range inputs, date/time, navigation, feedback/status,
  data display/gauges, containers and media. Plugin module filenames carry the
  same `01`-`09` prefixes because Qt Designer preserves first-discovery order
  instead of sorting the visible group labels.
- Stylesheet-backed `QColor` properties preserve alpha channels.
- Sliders support horizontal and vertical orientation; progress-bar height no
  longer overrides `textVisible`.
- `MonkezLCDNumber` deliberately uses only QLCDNumber's native decimal point;
  comma painting and locale/grouping separator properties have been removed.
  Literal commas are stripped for compatibility with older Designer forms.
  `displayFormatted(value, decimals)` produces an ungrouped dot-decimal value,
  while `displayText`, `number`, `decimalPlaces` and `autoDigitCount` remain.
  `digitColor` has component-level stylesheet priority over broad application
  styles while explicit per-widget styles can still override it.
- `MonkezPagination` adds Rounded, Pill, Minimal and Compact navigation styles,
  responsive ellipsis, page-count and item-count modes, mouse/keyboard/wheel
  navigation, state colors, runtime signals and a Designer style task menu.
- `MonkezTable` is a native high-performance model/view grid with mapping,
  sequence and object rows; typed columns/delegates; global and per-column
  filtering; stable multi-sort; local and server pagination; search debounce;
  selection/editing, CSV export and persisted column/query state. Designer and
  Gallery expose four visual styles and three density modes without WebEngine.
  Its outer frame, toolbar/footer corners and controls share one coherent
  geometry system; outer border width/radius and control height/radius are
  separately editable in Designer. The outer frame is painted above child
  surfaces to keep top corners crisp; sort chevrons and grouped pagination
  borders use platform-independent, high-DPI-aligned vector strokes. Selected
  rows share one subtle accent wash across every delegate, omit per-cell focus
  rectangles and use a slim leading marker.
- Eight practical components complete the feedback/navigation workflow:
  `MonkezStatusBadge`, `MonkezLoadingIndicator`, `MonkezLoadingOverlay`,
  runtime-only `MonkezToast`, `MonkezRangeSlider`, `MonkezSegmentedControl`,
  `MonkezFilePicker` and `MonkezBreadcrumb`. The seven visual form components
  have Designer plugins, Gallery previews, theme APIs and behavioral tests;
  Loading/Icon-only behavior is part of `MonkezButton`.
- `MonkezRadialGauge` exposes part-specific Designer/Python color names for
  active ticks, inactive ticks, the needle, central value and scale text while
  retaining the older generic color properties for compatibility.
- Gallery combines branding and search into one compact top row, and its Live
  Preview uses a centered grid cell so widgets with unusual size policies no
  longer drift toward or clip against the lower edge.
- Text buttons honor `textColor`; text-input trailing icons use completed-click
  semantics and do not retain stale hit areas after removal.
- Group-box child layouts reserve the header exactly once and refresh that
  geometry after font changes.
- Checkbox checked/partial marks, compact/RTL switches, and clamped linear-gauge
  targets are covered by rendering regression tests.
- Static checks are reproducible through `lint.bat` and the pinned `dev` extra.
- `MonkezCanva` provides a native runtime canvas editor supporting both release-
  Ctrl and held-Ctrl forms of the `Ctrl+D, E` chord, an owned floating palette,
  visible diagnostic logging, shapes, bar/line charts, flow
  nodes/connectors, grid snapping, JSON persistence and APIs for colors, text,
  chart data, highlight and animation. Deferred viewport fitting and bounded
  zoom prevent pre-show `fitContent()` calls from shrinking a graph to a dot.
  The editor now includes deep item inspection, stable ID/layer management,
  Explorer drag/drop for static images and GIF animation, viewport navigation,
  bounded undo/redo history, debounced autosave, process-local session
  checkpoints and application-data persistence with managed media copies.
  Edit mode also exposes a compact canvas-owned Save/zoom/fit/alignment floatbar
  that never shifts canvas geometry or scrolls with a panned viewport, a modern frameless draggable
  control pane, multi-select through the scene or Layers list, and right-button
  blank-canvas viewport pan. Pane/floatbar actions use a shared vector icon set;
  the title no longer carries an EDIT badge. View controls cover line/dot/cross
  grids, scene colors and fit/fill/scale background images. Persistent workspaces
  now live portably inside `.monkez_canva` in the project with relative managed
  assets and automatic legacy AppData migration. The element palette now includes
  diamond, triangle and a unified line whose points and arrowhead options cover
  straight lines, polylines and arrows. Connectors are selectable objects
  with stable IDs, editable endpoints, straight/bezier/orthogonal/polyline routes,
  stroke styles, one/two-way arrowheads and animated signal-flow overlays. The
  Inspector exposes only the content, media, chart, geometry, stroke, connector
  and appearance controls relevant to the selected object type. Nodes support
  configurable input/output/free ports (triangular input/output markers separated
  by color and a diamond free marker), direct port-to-port
  drag connection, directional validation and persisted connector endpoint IDs.
  Element/connector/object click signals are separated so connector selection no
  longer crashes element-only handlers. Inspector changes auto-apply with guarded
  debounce; the obsolete Apply Changes button has been removed.
  See `MONKEZ_CANVA_ARCHITECTURE.md`.

## Latest verification

- `MC-EDITOR-PALETTE-001` and `MC-EDITOR-COMMAND-001` provide a registry-driven
  searchable Add tab, category/Favorites/Recent filters, portable project
  preferences and a Ctrl+K command launcher. Command availability reflects
  registry, selection, clipboard, history and read-only state at open time.
  Favorites use icon-only stars; recent updates are part of the element Add
  command. Native Windows QA at 448x710 and 520x430 confirmed clean two-column
  tiles, unclipped search/filter controls and complete keyboard focus styling.

- `MC-EDITOR-SNAP-001` and `MC-EDITOR-CONTEXT-001` add deterministic Qt-free
  grid/edge/center/port snapping, transient smart guides, portable snap settings,
  context-aware blank/item/connector menus and atomic equal-size commands.
  Right-click without movement opens the canvas menu; right-drag continues to
  pan. The View pane is scroll-safe with compact icon viewport controls.

- `MC-EDITOR-OUTLINE-001` and `MC-EDITOR-MINIMAP-001` add a searchable scene
  outline, portable lock/hidden state, temporary isolation, a floating clickable
  minimap and portable viewport bookmarks. State changes are undoable and
  connectors automatically follow hidden endpoints.

- `MC-EDITOR-ROUTING-001` adds draggable reroute handles, rounded orthogonal
  paths, self-loops, edge labels and stable parallel lanes. A Qt-free routing
  module covers deterministic geometry; Inspector and public APIs persist every
  route parameter while packet/animation rendering follows the final path.

- `MC-EDITOR-SELECTION-001` begins Phase 2 with a strict, versioned graph
  clipboard. Ctrl+C/X/V and public APIs preserve internal connectors, remap IDs,
  endpoints and waypoints, and make cut/paste/duplicate atomic in history.
  Arrow, Shift+Arrow and Alt+Arrow nudge by 1/10/0.1 pixels with mergeable undo.
  Multi-selection Inspector fields display a real `Mixed` state and update only
  the explicitly changed common properties. Native Windows visual QA at 448x710
  confirmed readable mixed states, balanced geometry cards and unclipped controls.

- `MC-EDITOR-PANE-002` polishes the Floating Cards Control Pane at native Windows
  scale: its icon tabs are now a single compact segmented bar; all field/card
  spacing follows a consistent rhythm; geometry inputs expand as an even two-
  column grid; and packaged SVG chevrons replace the visually broken native
  spinbox button frames. Focus, hover, disabled and session-save states are now
  explicit and consistent.
- `MC-CORE-ANIMATION-001` completes Phase 1.5 with one canvas-owned animation
  clock for line/connector effects, packets and runtime property tweens. Hidden
  decorative effects pause, explicit packets still complete, and visible-scene
  culling avoids repainting every animated item on every tick. Runtime frame and
  repaint metrics are available through `animationStats()`.

- `MC-CORE-SCHEMA-001` completes Phase 1.4 with a public Draft 2020-12 document
  schema, a Qt-free ordered migration boundary, atomic JSON/asset writes, valid
  `.bak` recovery and SHA-256/size asset manifests. Both persistent and ordinary
  path loaders expose recovery/integrity signals and diagnostics. Documents or
  component records newer than runtime open visibly but read-only; UI, model,
  autosave and durable-save mutation paths are blocked. Windows visual QA at
  448x710 confirmed disabled mutation tabs, accessible Layers and an amber lock
  footer without clipping. The complete suite now contains 150 passing tests.

- `MC-CORE-HISTORY-001` replaces whole-document snapshots with bounded
  `QUndoStack` commands containing only changed record pairs. It covers model and
  graphics-origin edits, cascade delete, port/geometry/property edits,
  connection, grouping/resources, macro actions and identity-preserving rename.
  Continuous changes merge for 800 ms; toolbar/pane controls expose command text
  and enabled state, while durable save controls clean/dirty status.
  Windows visual QA confirmed the floating Undo/Redo icons, contextual command
  labels, disabled Redo state and coral `Draft saved` footer at 448x710.
- `MC-CORE-REGISTRY-001` foundation adds public component definitions and an
  ordered per-canvas registry. The Elements pane and element size/default lookup
  are metadata-driven; custom types can be registered without editing the pane,
  while unavailable project types load as safe missing-component placeholders.
  The registry now also validates schema definitions/records, runs contiguous
  component migrations, dispatches optional renderer and Inspector factories,
  drives standard Inspector sections by capability and tracks plugin ownership.
  Factory failures remain inside the plugin boundary and late registration
  restores placeholders without replacing IDs.
  Windows visual QA at 448x710 verified the scroll-bounded custom category and
  a contextual `Sensor properties` Inspector card without pane growth/clipping.
- `MC-CORE-MODEL-001` now provides a Qt-free `CanvasDocument` with immutable
  scene/element/connector/port/group/resource records, finite-JSON and graph
  validation, revisioned granular events, legacy line normalization, atomic
  rename/removal and synchronized multi-view attachment through
  `MonkezCanva.setDocumentModel()`. External operations now render incrementally;
  item identity, selection and viewport survive updates and renames. Public
  element/connector add, update, remove, rename and connect APIs commit model-first.
  Graphics-to-model reconciliation remains only as a transition layer for direct
  gestures and compound legacy actions.
- The Control Pane now follows the approved Floating Cards reference: warm white
  surface, coral accent, teal saved footer, selection-count badge, rounded cards,
  two-column geometry and a contextual eight-action multi-select arrange card.
  Horizontal/vertical distribution is a real document mutation. Windows-platform
  visual QA at 448x710 confirmed readable typography and no horizontal clipping.

- The complete MonkezCanva expansion has been accepted as an active long-term
  goal. `docs/MONKEZ_CANVA_MASTER_ROADMAP.md` records five delivery phases and
  quality gates; `agents/MONKEZ_CANVA_IMPLEMENTATION_PLAN.md` records module
  boundaries, sequencing, compatibility constraints and the first extraction
  milestone. The original dense Control Pane studies were replaced by five
  simpler concepts on 2026-08-09. The selected direction combines Option 1's
  common shell, Option 5's progressive disclosure, Option 3's contextual
  multi-selection actions, Option 4's narrow line controls and Option 2's dark
  theme. Runtime, Outline and Debugger remain separate detachable tools.

- MonkezCanva now renders output triangles outward, offers flow/pulse/glow/
  particles/packet effects on connectors and standalone lines, and persists
  direction, spacing, intensity and packet timing/icon/loop settings. The compact
  Inspector applies every field immediately and the pane uses an icon-led pill-tab
  visual system. Splitter elements provide one-to-many port junctions; addressable
  packets sent through `send_a_message()` propagate across all splitter branches.

- `MC-EDITOR-ROUTING-002` adds obstacle-aware auto routing, crossing bridges and
  `trunk`/`double` bus projection with portable clearance, bridge, width and bus-ID
  settings. Geometry helpers remain Qt-free; connector APIs, context actions and
  Inspector fields write canonical undoable records.
- `MC-EDITOR-PANE-003` refines the approved Floating Cards pane after native UI
  review: card titles sit inside an uninterrupted border, spin controls use subtle
  integrated stepper surfaces, and icon-led segmented tabs have a flatter selected
  state with tighter, consistent spacing.
- `MC-EDITOR-PANE-004` removes the remaining platform-dependent group-box
  artifacts. Inspector/View/Save cards now use one DPI-stable custom painter with
  inset titles, unbroken rounded borders and consistent padding. Spin controls
  use borderless inset steppers; the named five-tab bar has larger vector icons,
  one continuous segmented surface and explicit hover/selected outlines. Offscreen
  visual QA covered the full pane and the Position / size card at 438x720; the
  focused canvas document/widget suite contains 105 passing tests.
- `MC-EDITOR-GROUP-001` makes frame, swimlane and subflow first-class scene
  objects with stable IDs, nested cycle validation, collapse, atomic group move,
  fit-to-contents, Inspector/Layers/Minimap integration and JSON-only reusable
  templates with collision-safe import. Group rename preserves graphics identity.
- `MC-RUNTIME-TYPED-PORTS-001` completes the first Phase 3 slice. A shared Qt-free
  engine normalizes and enforces mode, data type, unit, required/default,
  cardinality and declared conversions. Model/API/reconnect/drag paths share its
  diagnostic result; green/purple/red candidate halos and preview pens expose
  direct/conversion/rejected targets. The Inspector edits every typed-port field
  and shows transient runtime state; runtime values emit signals but never persist.
  Schema, demo, public API tests and visual QA cover the new contract.
- `MC-EDITOR-LAYOUT-001` completes Phase 2. The Qt-free deterministic engine
  provides layered, tree, radial and force-directed strategies with cycle-safe
  hierarchy, connected-component packing, locked-node anchors and stable output.
  Smart document/selection/component/group scope is exposed through the View
  pane, context menus, Ctrl+K and public preview/apply APIs. Layout plus eligible
  group fitting commits as one undoable mutation. Offscreen QA at 438x720 confirms
  the compact conditional Force control and a five-node layered result without
  toolbar drift or canvas clipping.
- `MC-RUNTIME-PACKET-001` establishes packet runtime v2. Qt-free `MessageTicket`
  state covers transient payload/metadata, priority, hop TTL, timeout, terminal
  failure/cancel states, deterministic splitter policies and bounded ordered
  trace. Canvas APIs add non-blocking/async waits, pause/resume/step, object
  breakpoints, cancellation and runtime signals while keeping old
  `send_a_message()` behavior. A detached Runtime Debugger exposes ticket list,
  timeline, details and controls; breakpoint badges render directly on canvas.
  Headless coverage includes 1,000 concurrent tickets and offscreen QA captures
  two paused messages plus a frozen packet at a splitter graph.
- `MC-RUNTIME-WORKFLOW-001` adds the opt-in 29-component Workflow Pack and a
  deterministic Qt-free executor. Source/Sink boundaries, routing, timing and
  logic components compile from the portable document and support logical-time
  run/step/pause/resume/cancel, custom node/type handlers, bounded trace and
  cycle guards. Canvas projection adds transient node states, optional packet
  visualization, workflow signals, context/command actions, a dedicated
  Inspector card and a Workflow tab in Runtime Debugger. The demo runs a
  Source → Transform → Sink graph.
- `MC-EDITOR-PANE-005` completes another native Windows polish pass. Every pane
  number field now owns two compact borderless step buttons, eliminating the
  platform divider lines shown at non-default DPI. The five-tab segmented bar
  has balanced inset spacing, explicit selected icon color and a flatter active
  capsule; card title clearance, JSON fields and workflow state chips follow the
  same warm-white/coral/teal visual system. Offscreen visual QA covers the full
  pane and Position / size card at 438×720.
- `MC-RUNTIME-BINDING-001` completes the Phase 3 data-binding foundation. Portable
  element-local definitions target text/chart/appearance/geometry/typed ports and
  runtime highlight/animation without persisting live values. The Qt-free engine
  provides safe transform/format pipelines, deterministic debounce/throttle/stale,
  stale/error fallbacks, bounded trace and batch apply. Canvas source adapters cover
  push feeds, Qt signals/properties, callables, model indexes and external QObject
  adapters through one shared timer with explicit disconnect cleanup. Each element
  has a polished Data bindings Inspector card; Runtime Debugger adds a Bindings tab.
  Offscreen QA at 438×720 confirms the full editor fits without horizontal clipping.
- `MC-PACK-NATIVE-001` completes Phase 4 with 43 opt-in native components: 15
  Dashboard, 12 Industrial and 16 Software/Flowchart items. Qt-free immutable
  catalogs remain outside the default palette; enabling a pack attaches vector
  renderers, compact schema-driven property controls and typed ports. Blank-canvas
  menus, Ctrl+K and public APIs share the same pack state. Pack-specific properties
  support transient validated bindings such as `property.value`; disabling or a
  missing runtime preserves document records and stable IDs. Composite offscreen
  QA covers 12 representative items plus the selected Tank Inspector at 1638×760.
- `MC-ECOSYSTEM-EXPORT-001` begins Phase 5 with native scene/selection PNG,
  transparent PNG, SVG and PDF export; shared page configuration, native Page
  Setup and Print Preview; and Qt-free deterministic DOT/Mermaid output. Export
  transactions suppress editor artifacts and restore selection/visibility. The
  floatbar, context menu, Ctrl+K, public APIs and demo diagnostics share the same
  pipeline. Offscreen visual QA exported a 1102×670 mixed software/dashboard/
  industrial scene with clean bounds, grid and connectors and no editor chrome.
- `MC-ECOSYSTEM-EXCHANGE-002` adds safe constrained DOT import and
  import-as-subflow. A Qt-free bounded parser restores stable IDs, geometry,
  typed endpoint ports, arrows and styles; missing positions use deterministic
  layout. The widget remaps collisions, enables known native packs, degrades
  unknown types with diagnostics and commits the complete graph as one Undo step.
  Blank-canvas actions, Ctrl+K, public APIs and demo logs share the same path.
- The automated suite contains 228 tests and covers all 36 public
  runtime components and 35 Designer plugins.
- Canonical and legacy module launchers both report 0.5.0; source doctor
  verification targets all 35 Designer plugins.
- `monkez_pyqt6-0.5.0` wheel and source archive build successfully. An isolated
  wheel install imports the canonical package, compatibility namespace and all
  three UI-loading APIs successfully.
- The last portable release initializes and constructs its 34 Designer
  plugins successfully. A new portable build is still required to bundle and
  verify the 35th plugin, `MonkezCanva`.
- `MonkezDesigner-0.5.0-windows-x64.zip` contains 7,705 entries (266.6 MiB) and
  passes a full entry read/CRC integrity check.
- Its SHA-256 is
  `8783D89EA54C02A73DD6DE780D9462552291BD7E3DABE1D93987F3A2860D618B`.
- A real same-version running Designer triggered the timestamped build fallback;
  the isolated portable output then built, verified and archived successfully
  without terminating the existing process.
- Importing `MonkezImage` does not import NumPy. Updating and rendering thirty
  1280x720 BGR frames averaged 5.0 ms per frame on the release workstation.
- A real 0.4.7 portable Designer session successfully creates
  `scrollAreaWidgetContents` when `MonkezScrollArea` is dragged onto a blank
  form, then accepts and saves a `QLabel` dropped directly into that page.
- A real portable Designer session exposes all four Image scale actions from
  the `MonkezImage` context menu.
- Splash startup benchmark on the release workstation: import median 97.3 ms
  and first-paint median 133.8 ms.
- A standalone `SplashHeavyDemo.exe` exercises 48 MB of asset processing and a
  multi-stage CPU workload on a worker thread while reporting live splash progress.
- The full heavy-demo workload completes in approximately 13 seconds on the
  release workstation. Its 35.1 MB ZIP contains 189 entries and passes CRC
  integrity verification.

## Build policy

- PyInstaller is pinned to 6.21.0.
- The build verifies all Designer plugins before creating the release ZIP.
- The release script waits for the verified Designer process to release its
  embedded Python archive before compression.
- The portable archive is created with the .NET ZIP API to avoid the slow,
  noisy `Compress-Archive` progress loop.
- Unpacked portable builds use versioned output directories so an older
  running Designer does not block a new release build.
- A locked same-version output now falls back to a timestamped build directory,
  so rebuilding never requires forcibly closing the user's Designer window.
- QFluentWidgets and QFramelessWindow are deliberately bundled for the 0.5.0
  portable Designer work. Reassess their footprint before removing them.

## Known compatibility debt

- PyQt6 6.4.2 and its SIP bindings emit `sipPyTypeDict()` deprecation warnings
  under the current bridge. The pinned `pyqt6-tools` stack still requires this
  compatibility line; warnings do not currently fail tests.
- The one-folder portable distribution is large because it contains Qt, Python,
  OpenCV, NumPy, Designer bridge packages and Fluent dependencies.
