# Current engineering status

Updated: 2026-07-31

## Current version

- Working version: 0.4.7 (native ScrollArea behavior).
- Python runtime requires Python 3.10 or newer.
- Designer development and portable build require Python 3.11.

## Supported surface

- 25 runtime widgets.
- 25 Qt Designer plugins.
- Six themes: Material, iOS, Fluent, Bootstrap, Minimal and Dark.
- Runtime loading through `PyQt6.uic.loadUi()` and generated `pyuic6` code.
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
- `MonkezImage.scaleModeIndex` is a stable Designer property with task-menu
  choices for Fit, Fill, Stretch and Original; every mode recalculates against
  the outer container size.
- `MonkezScrollArea` preserves the stock `QScrollArea` runtime defaults and
  only adds theme/style properties. Its Designer XML uses Qt's native
  `scrollAreaWidgetContents` structure without a custom fixed-page extension.

## Latest verification

- 69 automated tests pass on Python 3.11.15, including native ScrollArea
  defaults, Designer DOM structure and runtime loading of a form saved by
  Designer with a nested `QLabel`.
- The 0.4.7 wheel and source distribution omit the former custom ScrollArea
  extension and include the native Designer page structure.
- The 0.4.7 portable executable passes `--doctor`; source and packaged plugin
  checks initialize and create all 25 plugins.
- A real 0.4.7 portable Designer session successfully creates
  `scrollAreaWidgetContents` when `MonkezScrollArea` is dragged onto a blank
  form, then accepts and saves a `QLabel` dropped directly into that page.
- A real portable Designer session exposes all four Image scale actions from
  the `MonkezImage` context menu.
- `MonkezDesigner-0.4.7-windows-x64.zip` contains 7,570 entries, includes all
  three portable launcher/onboarding files at its root and passes a full CRC
  integrity check.
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
- QFluentWidgets and QFramelessWindow are deliberately bundled for the 0.4.7
  portable Designer work. Reassess their footprint before removing them.

## Known compatibility debt

- PyQt6 6.4.2 and its SIP bindings emit `sipPyTypeDict()` deprecation warnings
  under the current bridge. The pinned `pyqt6-tools` stack still requires this
  compatibility line; warnings do not currently fail tests.
- The one-folder portable distribution is large because it contains Qt, Python,
  OpenCV, NumPy, Designer bridge packages and Fluent dependencies.
