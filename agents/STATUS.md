# Current engineering status

Updated: 2026-07-30

## Current version

- Released working version: 0.4.0.
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

## Latest verification

- 44 automated tests pass on Python 3.11.15.
- The 0.4.0 wheel and source distribution build successfully.
- The 0.4.0 portable executable passes its 25-plugin verification.
- `MonkezDesigner-0.4.0-windows-x64.zip` contains 7,595 entries and passes a
  full CRC integrity check.
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
- QFluentWidgets and QFramelessWindow are deliberately bundled for the 0.4.0
  portable Designer work. Reassess their footprint before removing them.

## Known compatibility debt

- PyQt6 6.4.2 and its SIP bindings emit `sipPyTypeDict()` deprecation warnings
  under the current bridge. The pinned `pyqt6-tools` stack still requires this
  compatibility line; warnings do not currently fail tests.
- The one-folder portable distribution is large because it contains Qt, Python,
  OpenCV, NumPy, Designer bridge packages and Fluent dependencies.
