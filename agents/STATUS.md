# Current engineering status

Updated: 2026-07-30

## Current version

- Working version: 0.3.8.
- Python runtime requires Python 3.10 or newer.
- Designer development and portable build require Python 3.11.

## Supported surface

- 24 runtime widgets.
- 24 Qt Designer plugins.
- Six themes: Material, iOS, Fluent, Bootstrap, Minimal and Dark.
- Runtime loading through `PyQt6.uic.loadUi()` and generated `pyuic6` code.
- Optional OpenCV camera support.

## Latest verification

- 37 automated tests pass on Python 3.11.15.
- The 0.3.8 wheel and source distribution build successfully.
- The portable executable passes its 24-plugin verification.
- The portable ZIP contains 7,589 entries and passes a full CRC integrity check.

## Build policy

- PyInstaller is pinned to 6.21.0.
- The build verifies all Designer plugins before creating the release ZIP.
- The release script waits for the verified Designer process to release its
  embedded Python archive before compression.
- QFluentWidgets and QFramelessWindow are deliberately bundled for the 0.3.8
  portable Designer work. Reassess their footprint before removing them.

## Known compatibility debt

- PyQt6 6.4.2 and its SIP bindings emit `sipPyTypeDict()` deprecation warnings
  under the current bridge. The pinned `pyqt6-tools` stack still requires this
  compatibility line; warnings do not currently fail tests.
- The one-folder portable distribution is large because it contains Qt, Python,
  OpenCV, NumPy, Designer bridge packages and Fluent dependencies.
