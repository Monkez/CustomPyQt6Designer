# Current engineering status

Updated: 2026-08-02

## Current version

- Working version: 0.5.0 (package rename and convenient UI loader).
- Python runtime requires Python 3.10 or newer.
- Designer development and portable build require Python 3.11.

## Supported surface

- 25 runtime widgets.
- 25 Qt Designer plugins.
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
- `MonkezImage` uses Ignored horizontal/vertical size policies and a zero
  minimum hint, so its outer layout owns widget geometry before the selected
  scale mode transforms the pixmap.
- `MonkezScrollArea` preserves the stock `QScrollArea` runtime defaults and
  only adds theme/style properties. Its Designer XML uses Qt's native
  `scrollAreaWidgetContents` structure without a custom fixed-page extension.
- Stylesheet-backed `QColor` properties preserve alpha channels.
- Sliders support horizontal and vertical orientation; progress-bar height no
  longer overrides `textVisible`.
- Text buttons honor `textColor`; text-input trailing icons use completed-click
  semantics and do not retain stale hit areas after removal.
- Group-box child layouts reserve the header exactly once and refresh that
  geometry after font changes.
- Checkbox checked/partial marks, compact/RTL switches, and clamped linear-gauge
  targets are covered by rendering regression tests.
- Static checks are reproducible through `lint.bat` and the pinned `dev` extra.

## Latest verification

- All 98 automated tests pass for 0.5.0.
- Canonical and legacy module launchers both report 0.5.0; source doctor
  verification passes with all 25 Designer plugins.
- `monkez_pyqt6-0.5.0` wheel and source archive build successfully. An isolated
  wheel install imports the canonical package, compatibility namespace and all
  three UI-loading APIs successfully.
- The current 0.5.0 portable build initializes and constructs all 25 Designer
  plugins successfully.
- `MonkezDesigner-0.5.0-windows-x64.zip` contains 7,590 entries (266.2 MB) and
  passes a full entry read/CRC integrity check.
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
