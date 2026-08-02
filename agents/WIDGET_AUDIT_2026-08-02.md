# Widget capability audit — 2026-08-02

The public surface was audited across runtime classes, inherited Qt behavior,
Designer properties/plugins, Gallery probes/previews, fluent aliases and tests.

## Decision

- Add the missing navigation primitive as `MonkezPagination` with a complete
  runtime/Designer/Gallery surface rather than a demo-only composite.
- Keep `MonkezLCDNumber` numeric formatting compact. The locale-configurable
  comma experiment was later removed in favor of the native decimal point only.
- Keep standard Qt capabilities inherited. Do not duplicate `QLineEdit`
  validation/echo/clear APIs, `QAbstractSlider` range/step APIs, combo editability,
  progress format, or date/time signals as parallel Monkez properties.

## Pagination contract

- Pages are 1-based and clamped to `[1, pageCount]`.
- `pageCount` is explicit mode; setting it clears `totalItems`.
- `totalItems` plus `pageSize` is calculated mode.
- Styles 0–3 are Rounded, Pill, Minimal and Compact.
- Mouse, Left/Right, PageUp/PageDown, Home/End and optional wheel navigation are
  supported. State changes emit `pageChanged` exactly once.
- The widget must remain lazy-imported and usable without Designer dependencies.

## Follow-up implementation

The practical feedback/navigation candidates were implemented after this audit:
status badge, loading indicator/overlay, runtime toast, range slider, segmented
control, file picker and breadcrumb. Loading and icon-only behavior were folded
into `MonkezButton` as selectable modes instead of adding two public widget
types. Slider value bubbles remain deferred until their interaction contract is
defined.

The Designer palette is ordered into nine workflow groups rather than grouping
unrelated controls by implementation base class. `MonkezScrollArea` also owns
automatic content-minimum tracking so AsNeeded scrollbars work for both layouts
and freely positioned Designer children while preserving explicit minimums.
