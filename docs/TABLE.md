# MonkezTable

`MonkezTable` is a native PyQt6 data grid designed for application tables,
device lists, production history and administration screens. It deliberately
uses Qt's model/view architecture instead of `QTableWidget` or WebEngine.

## Quick start

```python
from monkez_pyqt6.monkez_widgets import MonkezTable

table = MonkezTable()
table.setColumns([
    {"key": "name", "title": "Camera", "width": 180},
    {"key": "status", "title": "Status", "type": "badge"},
    {"key": "quality", "title": "Quality", "type": "progress"},
    {"key": "enabled", "title": "Enabled", "type": "boolean"},
])
table.setRows([
    {"name": "Camera 01", "status": "Online", "quality": 96, "enabled": True},
    {"name": "Camera 02", "status": "Offline", "quality": 42, "enabled": False},
])
```

Rows may be dictionaries, sequences or objects. Dictionary/object columns use
the configured `key`; sequence rows use the column position.

## Column schema

| Field | Meaning |
|---|---|
| `key` / `field` | Unique data key. |
| `title` / `header` | Header text. |
| `type` | `text`, `number`, `currency`, `boolean`, `progress` or `badge`. |
| `width`, `min_width` | Initial and minimum width. |
| `editable` | Allow editing when the table-level `editable` property is enabled. |
| `sortable`, `filterable`, `visible` | Per-column feature switches. |
| `format` | Python format template such as `"{:.2f}"`. |
| `alignment` | Qt alignment flags. |

For reusable schemas, import `MonkezTableColumn` from
`monkez_pyqt6.monkez_widgets.monkez_table` and construct instances directly.

## Local data workflow

```python
table.setPageSize(50)
table.setSearchText("camera")
table.setColumnFilter("status", "online")
table.setSort("status")
table.setSort("quality", descending=True, additive=True)
```

Local pagination is applied after filtering and sorting. The page proxy exposes
only the current row window and does not copy the underlying row objects.
Search input is debounced to avoid filtering on every keystroke.

## Server-side workflow

```python
table.setServerMode(True)

def load_query(query):
    # query: page, pageSize, search, filters, sort
    rows, total = api.fetch_rows(query)
    table.setRows(rows, total=total)

table.queryChanged.connect(load_query)
table.setTotalItems(125_000)
```

In server mode, the current page is displayed without applying the query a
second time locally. Search, filters, sorting, page and page size changes emit
one structured `queryChanged` payload for the application data provider.

## Selection, editing and actions

- `selectedRows()` returns original row objects, not display strings.
- `rowActivated` emits the original row on double-click.
- Set table `editable=True` and column `editable=True` to edit a cell.
- `cellEdited(row, key, value)` reports successful edits.
- `Ctrl+C` or `copySelection()` copies selected cells as tab-separated text.
- `exportCsv(path)` exports filtered rows and respects hidden columns.

## Appearance and saved state

`styleIndex` selects Modern, Bordered, Minimal or Card. `densityIndex` selects
Compact, Default or Comfortable row height. Both are available from the Qt
Designer context menu together with all six Monkez themes.

Designer also exposes `backgroundColor`, `alternateRowColor`,
`headerBackgroundColor`, `textColor`, `borderColor` and `accentColor`. Fluent
helpers such as `setBackground()`, `setForeground()`, `setBorder()` and
`setAccent()` map to the same color roles.

The outer frame and toolbar controls can be tuned independently with
`borderWidth`, `borderRadius`, `controlRadius` and `controlHeight`. The default
table uses a one-pixel rounded outer frame and consistent 36-pixel search,
column-menu and page-size controls. Set `borderWidth=0` for a borderless embed,
or increase `borderRadius` for a card-like surface. These properties are also
available directly in Qt Designer.

Sorted columns use a crisp vector chevron drawn by the table itself instead of
the platform-dependent Qt indicator. Ascending and descending states remain
aligned at the right edge of the header; multi-column sorting also shows the
sort priority. The outer frame and Compact/Pill pagination frames use
pixel-aligned strokes so one-pixel rounded borders stay even at high DPI.

Selected rows use one low-contrast accent wash across text, badge and progress
cells, preserve semantic badge colors, remove the platform focus rectangle and
add a slim accent marker at the leading edge. This keeps selection visible
without replacing the row's information colors.

`saveState()` returns a JSON-compatible dictionary containing column order,
widths and visibility plus search, filters, sort, page size, style and density.
Pass the dictionary back to `restoreState()` after recreating the same schema.

## Performance notes

- The source model stores one reference per row and reads values on demand.
- Filtering uses case-folded comparisons and sorting compares raw typed values.
- Pagination is a proxy window rather than a second list of row data.
- For very large remote datasets, use `serverMode=True`; do database/API filter,
  sort and pagination outside the GUI thread and return only the requested page.
