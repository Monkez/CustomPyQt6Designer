# Current engineering status

Updated: 2026-07-31

## Current version

- Working version: 0.4.6 (Designer Image scale modes).
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
- `MonkezScrollArea` registers a fixed-page Designer container extension so
  widgets can be dropped onto and saved inside `scrollAreaWidgetContents`.

## Latest verification

- 68 automated tests pass on Python 3.11.15, including all Image scale modes,
  Designer property UI loading, ScrollArea container-extension routing, ScrollArea
  child UI loading and rendered-pixel stylesheet checks.
- The 0.4.6 wheel and source distribution include the Image scale-mode and
  ScrollArea Designer-container fixes.
- The 0.4.6 portable executable passes `--doctor`, creates a new splash form
  through `--new-splash`, and opens it during the 25-plugin verification.
- A real portable Designer session accepts a `QLabel` dropped into
  `MonkezScrollArea.scrollAreaWidgetContents`.
- A real portable Designer session exposes all four Image scale actions from
  the `MonkezImage` context menu.
- `MonkezDesigner-0.4.6-windows-x64.zip` contains 7,571 entries, includes all
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
- QFluentWidgets and QFramelessWindow are deliberately bundled for the 0.4.6
  portable Designer work. Reassess their footprint before removing them.

## Known compatibility debt

- PyQt6 6.4.2 and its SIP bindings emit `sipPyTypeDict()` deprecation warnings
  under the current bridge. The pinned `pyqt6-tools` stack still requires this
  compatibility line; warnings do not currently fail tests.
- The one-folder portable distribution is large because it contains Qt, Python,
  OpenCV, NumPy, Designer bridge packages and Fluent dependencies.
