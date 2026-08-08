# Current engineering status

Updated: 2026-08-08

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

- The complete MonkezCanva expansion has been accepted as an active long-term
  goal. `docs/MONKEZ_CANVA_MASTER_ROADMAP.md` records five delivery phases and
  quality gates; `agents/MONKEZ_CANVA_IMPLEMENTATION_PLAN.md` records module
  boundaries, sequencing, compatibility constraints and the first extraction
  milestone. Five Control Pane concepts have been generated, stored in project
  docs and evaluated. The selected direction combines Option 1's contextual
  Inspector, Option 3's multi-selection controls and Option 2's dark treatment;
  Options 4 and 5 become specialized Industrial and Debugger workspaces.

- MonkezCanva now renders output triangles outward, offers flow/pulse/glow/
  particles/packet effects on connectors and standalone lines, and persists
  direction, spacing, intensity and packet timing/icon/loop settings. The compact
  Inspector applies every field immediately and the pane uses an icon-led pill-tab
  visual system. Splitter elements provide one-to-many port junctions; addressable
  packets sent through `send_a_message()` propagate across all splitter branches.

- The automated suite contains 122 passing tests and covers all 36 public
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
