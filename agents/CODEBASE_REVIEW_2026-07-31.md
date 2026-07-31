# Codebase review — 2026-07-31

## Scope

Reviewed all 25 runtime widgets, all 25 Designer plugins, the lazy export layer,
UI loader, splash/startup helpers, tests, packaging metadata and Windows helper
scripts. The pre-existing user change in `examples/splash_screen.ui` was not
modified.

## Correctness fixes

- `MonkezButton` Text mode now honors `textColor`; keyboard/mouse pressed state
  follows `QAbstractButton.isDown()` and ignores right-click.
- `MonkezTextInput` clears a stale trailing-icon hit rectangle when the icon is
  removed and emits `trailingIconClicked` on completed click rather than press.
- `MonkezProgressBar.barHeight` no longer silently and irreversibly changes
  `textVisible`.
- `MonkezSlider` has vertical groove/fill/handle rules and orientation-aware
  size hints.
- `MonkezGroupBox` no longer applies header/content padding twice. Font changes
  immediately recompute reserved header geometry.
- `MonkezCheckBox` explicitly paints checked and partially checked marks.
- `MonkezSwitch` handles compact geometry, disabled/focus states and RTL layout.
- Linear gauge target markers are clamped to the visible track.
- Empty combo boxes do not open a blank popup.
- Image task menus no longer show six non-functional theme actions.

## Consistency and performance

- Added `color_to_css()` and routed stylesheet-backed customizable colors
  through it so alpha channels are not discarded by `QColor.name()`.
- Button and text-input shadow effects are reused when properties change.
- Removed unused imports identified by static analysis.
- Added a pinned `dev` extra, repository Ruff policy and `lint.bat`.
- Portable builds detect a locked same-version executable and switch to an
  isolated timestamped output directory without terminating the user's app.

## Verification policy

- Keep `lint.bat` green.
- Keep `test.bat` green in offscreen Qt mode.
- Run `build.bat` for release-affecting widget or plugin changes.
- Hardware camera release checks must still be performed on representative
  devices/backends because CI cannot prove driver behavior.
