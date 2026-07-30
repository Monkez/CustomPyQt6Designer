# Current engineering status

Updated: 2026-07-30

## Current version

- Working version: 0.4.3 (standalone Designer splash workflow).
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

## Latest verification

- 58 automated tests pass on Python 3.11.15.
- The 0.4.3 wheel and source distribution build successfully and contain the
  standalone splash template.
- The 0.4.3 portable executable passes `--doctor`, creates a new splash form
  through `--new-splash`, and opens it during the 25-plugin verification.
- `MonkezDesigner-0.4.3-windows-x64.zip` contains 7,569 entries, includes all
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
- QFluentWidgets and QFramelessWindow are deliberately bundled for the 0.4.3
  portable Designer work. Reassess their footprint before removing them.

## Known compatibility debt

- PyQt6 6.4.2 and its SIP bindings emit `sipPyTypeDict()` deprecation warnings
  under the current bridge. The pinned `pyqt6-tools` stack still requires this
  compatibility line; warnings do not currently fail tests.
- The one-folder portable distribution is large because it contains Qt, Python,
  OpenCV, NumPy, Designer bridge packages and Fluent dependencies.
