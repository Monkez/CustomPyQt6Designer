from __future__ import annotations

import csv
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PyQt6.QtCore import (
    QAbstractProxyModel,
    QAbstractTableModel,
    QModelIndex,
    QPoint,
    QSortFilterProxyModel,
    Qt,
    QTimer,
    pyqtProperty,
    pyqtSignal,
)
from PyQt6.QtGui import QAction, QColor, QFont, QKeySequence, QPainter, QPen, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QSizePolicy,
    QStyledItemDelegate,
    QStyle,
    QStyleOptionViewItem,
    QTableView,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from .monkez_pagination import MonkezPagination
from .theme_support import ThemeSupportMixin
from .themes import color_to_css, theme_color, theme_radius


RAW_VALUE_ROLE = int(Qt.ItemDataRole.UserRole) + 1
COLUMN_KEY_ROLE = RAW_VALUE_ROLE + 1
COLUMN_TYPE_ROLE = RAW_VALUE_ROLE + 2


@dataclass(frozen=True, slots=True)
class MonkezTableColumn:
    """Declarative column schema used by :class:`MonkezTable`."""

    key: str
    title: str = ""
    data_type: str = "text"
    width: int = 140
    minimum_width: int = 56
    alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
    editable: bool = False
    sortable: bool = True
    filterable: bool = True
    visible: bool = True
    format: str = ""

    @classmethod
    def from_value(cls, value: str | Mapping[str, Any] | "MonkezTableColumn") -> "MonkezTableColumn":
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            return cls(value, value.replace("_", " ").title())
        data = dict(value)
        key = str(data.pop("key", data.pop("field", ""))).strip()
        if not key:
            raise ValueError("A table column requires a non-empty 'key' or 'field'.")
        aliases = {
            "type": "data_type",
            "min_width": "minimum_width",
            "header": "title",
        }
        for old, new in aliases.items():
            if old in data and new not in data:
                data[new] = data.pop(old)
        data.setdefault("title", key.replace("_", " ").title())
        return cls(key=key, **data)


def _row_value(row: Any, key: str, column: int) -> Any:
    if isinstance(row, Mapping):
        return row.get(key)
    if isinstance(row, Sequence) and not isinstance(row, (str, bytes, bytearray)):
        return row[column] if column < len(row) else None
    return getattr(row, key, None)


def _display_value(value: Any, column: MonkezTableColumn) -> str:
    if value is None:
        return ""
    if column.format:
        try:
            return column.format.format(value)
        except (ValueError, KeyError, IndexError):
            pass
    kind = column.data_type.lower()
    if kind == "boolean":
        return "Yes" if bool(value) else "No"
    if kind == "currency":
        try:
            return f"{float(value):,.2f}"
        except (TypeError, ValueError):
            return str(value)
    if kind == "number":
        return f"{value:,}" if isinstance(value, int) else str(value)
    if kind == "progress":
        try:
            return f"{float(value):g}%"
        except (TypeError, ValueError):
            return str(value)
    return str(value)


class MonkezTableModel(QAbstractTableModel):
    """Fast, allocation-light table model for mappings, sequences and objects."""

    cellEdited = pyqtSignal(int, str, object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._columns: tuple[MonkezTableColumn, ...] = ()
        self._rows: list[Any] = []

    @property
    def columns(self) -> tuple[MonkezTableColumn, ...]:
        return self._columns

    @property
    def rows(self) -> list[Any]:
        return self._rows

    def setColumns(self, columns: Sequence[str | Mapping[str, Any] | MonkezTableColumn]) -> None:
        parsed = tuple(MonkezTableColumn.from_value(column) for column in columns)
        keys = [column.key for column in parsed]
        if len(keys) != len(set(keys)):
            raise ValueError("Table column keys must be unique.")
        self.beginResetModel()
        self._columns = parsed
        self.endResetModel()

    def setRows(self, rows: Sequence[Any] | None) -> None:
        self.beginResetModel()
        self._rows = list(rows or ())
        self.endResetModel()

    def appendRows(self, rows: Sequence[Any]) -> None:
        incoming = list(rows)
        if not incoming:
            return
        first = len(self._rows)
        self.beginInsertRows(QModelIndex(), first, first + len(incoming) - 1)
        self._rows.extend(incoming)
        self.endInsertRows()

    def clear(self) -> None:
        self.setRows(())

    def updateRow(self, row: int, values: Mapping[str, Any]) -> bool:
        if not 0 <= row < len(self._rows):
            return False
        target = self._rows[row]
        if isinstance(target, dict):
            target.update(values)
        else:
            for key, value in values.items():
                if hasattr(target, key):
                    setattr(target, key, value)
        if self._columns:
            self.dataChanged.emit(self.index(row, 0), self.index(row, len(self._columns) - 1))
        return True

    def removeRows(self, row: int, count: int, parent=QModelIndex()) -> bool:
        if parent.isValid() or count <= 0 or row < 0 or row + count > len(self._rows):
            return False
        self.beginRemoveRows(parent, row, row + count - 1)
        del self._rows[row : row + count]
        self.endRemoveRows()
        return True

    def rowData(self, row: int) -> Any:
        return self._rows[row] if 0 <= row < len(self._rows) else None

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._columns)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._rows) or index.column() >= len(self._columns):
            return None
        column = self._columns[index.column()]
        value = _row_value(self._rows[index.row()], column.key, index.column())
        if role == Qt.ItemDataRole.DisplayRole:
            return _display_value(value, column)
        if role in (Qt.ItemDataRole.EditRole, RAW_VALUE_ROLE):
            return value
        if role == COLUMN_KEY_ROLE:
            return column.key
        if role == COLUMN_TYPE_ROLE:
            return column.data_type
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return int(column.alignment)
        if role == Qt.ItemDataRole.ToolTipRole:
            text = _display_value(value, column)
            return text if len(text) > 32 else None
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal and section < len(self._columns):
                return self._columns[section].title
            if orientation == Qt.Orientation.Vertical:
                return section + 1
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return int(Qt.AlignmentFlag.AlignCenter)
        return None

    def flags(self, index: QModelIndex):
        flags = super().flags(index) | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        if index.isValid() and self._columns[index.column()].editable:
            flags |= Qt.ItemFlag.ItemIsEditable
        return flags

    def setData(self, index: QModelIndex, value: Any, role=Qt.ItemDataRole.EditRole) -> bool:
        if role != Qt.ItemDataRole.EditRole or not index.isValid():
            return False
        column = self._columns[index.column()]
        if not column.editable:
            return False
        row = self._rows[index.row()]
        if isinstance(row, dict):
            row[column.key] = value
        elif isinstance(row, list) and index.column() < len(row):
            row[index.column()] = value
        elif hasattr(row, column.key):
            setattr(row, column.key, value)
        else:
            return False
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole])
        self.cellEdited.emit(index.row(), column.key, value)
        return True


class MonkezTableFilterProxy(QSortFilterProxyModel):
    """Global/per-column filtering plus stable multi-column sorting."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._query = ""
        self._filters: dict[str, str] = {}
        self._sort_keys: list[tuple[int, Qt.SortOrder]] = []
        self.setDynamicSortFilter(True)
        self.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def setSearchText(self, text: str) -> None:
        value = str(text).strip().casefold()
        if value != self._query:
            self._query = value
            self.invalidateFilter()

    def setColumnFilter(self, key: str, value: str) -> None:
        text = str(value).strip().casefold()
        if text:
            self._filters[str(key)] = text
        else:
            self._filters.pop(str(key), None)
        self.invalidateFilter()

    def clearFilters(self) -> None:
        if self._query or self._filters:
            self._query = ""
            self._filters.clear()
            self.invalidateFilter()

    def filters(self) -> dict[str, str]:
        return dict(self._filters)

    def setSortKeys(self, keys: Sequence[tuple[int, Qt.SortOrder]]) -> None:
        self._sort_keys = list(keys)
        self.invalidate()
        if self._sort_keys:
            self.sort(0, Qt.SortOrder.AscendingOrder)

    def sortKeys(self) -> tuple[tuple[int, Qt.SortOrder], ...]:
        return tuple(self._sort_keys)

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model = self.sourceModel()
        if model is None:
            return False
        global_match = not self._query
        for column in range(model.columnCount(source_parent)):
            index = model.index(source_row, column, source_parent)
            text = str(model.data(index, Qt.ItemDataRole.DisplayRole) or "").casefold()
            if self._query and self._query in text:
                global_match = True
            key = str(model.data(index, COLUMN_KEY_ROLE) or "")
            filter_text = self._filters.get(key)
            if filter_text and filter_text not in text:
                return False
        return global_match

    @staticmethod
    def _compare(left: Any, right: Any) -> int:
        if left is None and right is None:
            return 0
        if left is None:
            return -1
        if right is None:
            return 1
        try:
            return (left > right) - (left < right)
        except TypeError:
            a, b = str(left).casefold(), str(right).casefold()
            return (a > b) - (a < b)

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        model = self.sourceModel()
        if model is None:
            return False
        keys = self._sort_keys or [(left.column(), Qt.SortOrder.AscendingOrder)]
        for column, order in keys:
            a = model.data(model.index(left.row(), column), RAW_VALUE_ROLE)
            b = model.data(model.index(right.row(), column), RAW_VALUE_ROLE)
            result = self._compare(a, b)
            if result:
                return result < 0 if order == Qt.SortOrder.AscendingOrder else result > 0
        return left.row() < right.row()


class MonkezTablePageProxy(QAbstractProxyModel):
    """Zero-copy row window over a filtered model."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._page = 1
        self._page_size = 20
        self._enabled = True

    def setSourceModel(self, source_model) -> None:
        old = self.sourceModel()
        if old is not None:
            for signal in (old.modelReset, old.layoutChanged, old.rowsInserted, old.rowsRemoved):
                try:
                    signal.disconnect(self._reset)
                except TypeError:
                    pass
        self.beginResetModel()
        super().setSourceModel(source_model)
        if source_model is not None:
            source_model.modelReset.connect(self._reset)
            source_model.layoutChanged.connect(self._reset)
            source_model.rowsInserted.connect(self._reset)
            source_model.rowsRemoved.connect(self._reset)
            source_model.dataChanged.connect(self._source_data_changed)
        self.endResetModel()

    def _reset(self, *args) -> None:
        self.beginResetModel()
        self.endResetModel()

    def _source_data_changed(self, *args) -> None:
        if self.rowCount():
            self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount() - 1, max(0, self.columnCount() - 1)))

    def setPage(self, page: int) -> None:
        page = max(1, int(page))
        if page != self._page:
            self.beginResetModel()
            self._page = page
            self.endResetModel()

    def setPageSize(self, size: int) -> None:
        size = max(1, int(size))
        if size != self._page_size:
            self.beginResetModel()
            self._page_size = size
            self.endResetModel()

    def setEnabled(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled != self._enabled:
            self.beginResetModel()
            self._enabled = enabled
            self.endResetModel()

    def _offset(self) -> int:
        return (self._page - 1) * self._page_size if self._enabled else 0

    def rowCount(self, parent=QModelIndex()) -> int:
        source = self.sourceModel()
        if parent.isValid() or source is None:
            return 0
        count = max(0, source.rowCount() - self._offset())
        return min(self._page_size, count) if self._enabled else count

    def columnCount(self, parent=QModelIndex()) -> int:
        source = self.sourceModel()
        return 0 if parent.isValid() or source is None else source.columnCount()

    def index(self, row: int, column: int, parent=QModelIndex()) -> QModelIndex:
        if parent.isValid() or row < 0 or column < 0 or row >= self.rowCount() or column >= self.columnCount():
            return QModelIndex()
        return self.createIndex(row, column)

    def parent(self, child: QModelIndex) -> QModelIndex:
        return QModelIndex()

    def mapToSource(self, proxy_index: QModelIndex) -> QModelIndex:
        source = self.sourceModel()
        if not proxy_index.isValid() or source is None:
            return QModelIndex()
        return source.index(proxy_index.row() + self._offset(), proxy_index.column())

    def mapFromSource(self, source_index: QModelIndex) -> QModelIndex:
        if not source_index.isValid():
            return QModelIndex()
        row = source_index.row() - self._offset()
        return self.index(row, source_index.column()) if 0 <= row < self.rowCount() else QModelIndex()

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        source = self.sourceModel()
        return None if source is None else source.data(self.mapToSource(index), role)

    def setData(self, index: QModelIndex, value: Any, role=Qt.ItemDataRole.EditRole) -> bool:
        source = self.sourceModel()
        return False if source is None else source.setData(self.mapToSource(index), value, role)

    def flags(self, index: QModelIndex):
        source = self.sourceModel()
        return Qt.ItemFlag.NoItemFlags if source is None else source.flags(self.mapToSource(index))

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        source = self.sourceModel()
        if source is None:
            return None
        if orientation == Qt.Orientation.Vertical and role == Qt.ItemDataRole.DisplayRole:
            return section + self._offset() + 1
        return source.headerData(section, orientation, role)


class MonkezTableDelegate(QStyledItemDelegate):
    def __init__(self, table: "MonkezTable") -> None:
        super().__init__(table)
        self._table = table

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        kind = str(index.data(COLUMN_TYPE_ROLE) or "").lower()
        if kind not in {"boolean", "progress", "badge"}:
            super().paint(painter, option, index)
            return
        base = QStyleOptionViewItem(option)
        self.initStyleOption(base, index)
        base.text = ""
        self._table.style().drawControl(QStyle.ControlElement.CE_ItemViewItem, base, painter, self._table)
        rect = option.rect.adjusted(10, 7, -10, -7)
        value = index.data(RAW_VALUE_ROLE)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if kind == "progress":
            try:
                progress = max(0.0, min(100.0, float(value)))
            except (TypeError, ValueError):
                progress = 0.0
            bar = rect.adjusted(0, max(0, (rect.height() - 8) // 2), 0, -max(0, (rect.height() - 8) // 2))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self._table._surface_alt)
            painter.drawRoundedRect(bar, 4, 4)
            fill = bar.adjusted(0, 0, -round(bar.width() * (1 - progress / 100)), 0)
            painter.setBrush(self._table._accent)
            painter.drawRoundedRect(fill, 4, 4)
            painter.setPen(self._table._text)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{progress:g}%")
        else:
            text = ("Yes" if bool(value) else "No") if kind == "boolean" else str(value or "")
            positive = bool(value) if kind == "boolean" else text.casefold() in {
                "active", "online", "success", "complete", "completed", "approved",
            }
            negative = text.casefold() in {"error", "failed", "offline", "rejected", "danger"}
            color = self._table._success if positive else (self._table._danger if negative else self._table._accent)
            metrics = option.fontMetrics
            width = min(rect.width(), metrics.horizontalAdvance(text) + 22)
            pill = rect
            pill.setWidth(width)
            pill.moveCenter(rect.center())
            bg = QColor(color)
            bg.setAlpha(35)
            painter.setPen(QPen(color, 1))
            painter.setBrush(bg)
            painter.drawRoundedRect(pill, pill.height() / 2, pill.height() / 2)
            painter.setPen(color)
            painter.drawText(pill, Qt.AlignmentFlag.AlignCenter, text)
        painter.restore()


class MonkezTable(QWidget, ThemeSupportMixin):
    """Modern model/view data table with local and server-side workflows."""

    themeChanged = pyqtSignal(str)
    pageChanged = pyqtSignal(int)
    pageSizeChanged = pyqtSignal(int)
    filtersChanged = pyqtSignal(object)
    sortChanged = pyqtSignal(object)
    queryChanged = pyqtSignal(object)
    rowActivated = pyqtSignal(object)
    selectedRowsChanged = pyqtSignal(object)
    cellEdited = pyqtSignal(int, str, object)

    STYLE_NAMES = ("Modern", "Bordered", "Minimal", "Card")
    DENSITY_NAMES = ("Compact", "Default", "Comfortable")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._init_theme_support()
        self._style_index = 0
        self._density_index = 1
        self._search_enabled = True
        self._filters_enabled = True
        self._sorting_enabled = True
        self._multi_sort_enabled = True
        self._pagination_enabled = True
        self._server_mode = False
        self._remote_total = 0
        self._editable = False
        self._row_numbers = False
        self._column_lines = False
        self._toolbar_visible = True
        self._footer_visible = True
        self._empty_text = "No data to display"
        self._loading_text = "Loading data..."
        self._loading = False
        self._sort_keys: list[tuple[int, Qt.SortOrder]] = []
        self._column_filters: dict[str, str] = {}

        self._model = MonkezTableModel(self)
        self._filter_proxy = MonkezTableFilterProxy(self)
        self._filter_proxy.setSourceModel(self._model)
        self._page_proxy = MonkezTablePageProxy(self)
        self._page_proxy.setSourceModel(self._filter_proxy)

        self._build_ui()
        self._connect_signals()
        self.setFont(QFont("Segoe UI", 9))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAccessibleName("Data table")
        self.setTheme("material")

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._toolbar = QWidget(self)
        self._toolbar.setObjectName("monkezTableToolbar")
        tools = QHBoxLayout(self._toolbar)
        tools.setContentsMargins(12, 10, 12, 10)
        tools.setSpacing(8)
        self._search = QLineEdit(self._toolbar)
        self._search.setObjectName("monkezTableSearch")
        self._search.setPlaceholderText("Search all columns...")
        self._search.setClearButtonEnabled(True)
        self._search.setMaximumWidth(340)
        self._search.setAccessibleName("Search table")
        tools.addWidget(self._search, 1)
        tools.addStretch(1)
        self._columns_button = QToolButton(self._toolbar)
        self._columns_button.setObjectName("monkezTableColumns")
        self._columns_button.setText("Columns")
        self._columns_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        tools.addWidget(self._columns_button)
        root.addWidget(self._toolbar)

        self._view = QTableView(self)
        self._view.setObjectName("monkezTableView")
        self._view.setModel(self._page_proxy)
        self._view.setItemDelegate(MonkezTableDelegate(self))
        self._view.setAlternatingRowColors(True)
        self._view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._view.setSortingEnabled(False)
        self._view.setShowGrid(False)
        self._view.setWordWrap(False)
        self._view.setTextElideMode(Qt.TextElideMode.ElideRight)
        self._view.setCornerButtonEnabled(False)
        self._view.verticalHeader().setVisible(False)
        self._view.verticalHeader().setDefaultSectionSize(42)
        header = self._view.horizontalHeader()
        header.setSectionsMovable(True)
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(False)
        header.setStretchLastSection(True)
        header.setMinimumSectionSize(48)
        header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        root.addWidget(self._view, 1)

        self._state_label = QLabel(self._view.viewport())
        self._state_label.setObjectName("monkezTableState")
        self._state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._state_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._state_label.hide()

        self._footer = QWidget(self)
        self._footer.setObjectName("monkezTableFooter")
        footer = QHBoxLayout(self._footer)
        footer.setContentsMargins(12, 8, 12, 8)
        footer.setSpacing(10)
        self._summary = QLabel(self._footer)
        self._summary.setObjectName("monkezTableSummary")
        footer.addWidget(self._summary)
        footer.addStretch(1)
        self._pagination = MonkezPagination(self._footer)
        self._pagination.setStyleIndex(3)
        self._pagination.setButtonSize(30)
        self._pagination.setCurrentPage(1)
        footer.addWidget(self._pagination)
        self._page_size_combo = QComboBox(self._footer)
        self._page_size_combo.setObjectName("monkezTablePageSize")
        self._page_size_combo.addItems(["10", "20", "50", "100", "250"])
        self._page_size_combo.setCurrentText("20")
        self._page_size_combo.setAccessibleName("Rows per page")
        footer.addWidget(self._page_size_combo)
        root.addWidget(self._footer)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(180)
        self._copy_shortcut = QShortcut(QKeySequence.StandardKey.Copy, self._view)

    def _connect_signals(self) -> None:
        self._search.textChanged.connect(lambda: self._search_timer.start())
        self._search_timer.timeout.connect(self._apply_search)
        self._pagination.pageChanged.connect(self._change_page)
        self._page_size_combo.currentTextChanged.connect(lambda text: self.setPageSize(int(text)))
        self._view.horizontalHeader().sectionClicked.connect(self._header_clicked)
        self._view.horizontalHeader().customContextMenuRequested.connect(self._show_header_menu)
        self._view.doubleClicked.connect(self._activate_index)
        self._view.selectionModel().selectionChanged.connect(self._selection_changed)
        self._model.cellEdited.connect(self.cellEdited)
        self._filter_proxy.modelReset.connect(self._refresh_paging)
        self._filter_proxy.rowsInserted.connect(self._refresh_paging)
        self._filter_proxy.rowsRemoved.connect(self._refresh_paging)
        self._copy_shortcut.activated.connect(self.copySelection)

    def tableView(self) -> QTableView:
        return self._view

    def sourceModel(self) -> MonkezTableModel:
        return self._model

    def setColumns(self, columns: Sequence[str | Mapping[str, Any] | MonkezTableColumn]) -> None:
        self._model.setColumns(columns)
        header = self._view.horizontalHeader()
        for index, column in enumerate(self._model.columns):
            header.resizeSection(index, max(column.minimum_width, column.width))
            self._view.setColumnHidden(index, not column.visible)
        self._rebuild_columns_menu()
        self._refresh_paging()

    def columns(self) -> tuple[MonkezTableColumn, ...]:
        return self._model.columns

    def setRows(self, rows: Sequence[Any] | None, total: int | None = None) -> None:
        self._model.setRows(rows)
        if total is not None:
            self._remote_total = max(0, int(total))
        self._refresh_paging()

    def appendRows(self, rows: Sequence[Any]) -> None:
        self._model.appendRows(rows)
        self._refresh_paging()

    def updateRow(self, source_row: int, values: Mapping[str, Any]) -> bool:
        return self._model.updateRow(int(source_row), values)

    def removeRow(self, source_row: int) -> bool:
        removed = self._model.removeRows(int(source_row), 1)
        if removed:
            self._refresh_paging()
        return removed

    def clear(self) -> None:
        self._model.clear()
        self._refresh_paging()

    def rows(self) -> tuple[Any, ...]:
        return tuple(self._model.rows)

    def filteredRowCount(self) -> int:
        return self._filter_proxy.rowCount()

    def visibleRowCount(self) -> int:
        return self._page_proxy.rowCount()

    def rowData(self, visible_row: int) -> Any:
        index = self._page_proxy.index(visible_row, 0)
        filtered = self._page_proxy.mapToSource(index)
        source = self._filter_proxy.mapToSource(filtered)
        return self._model.rowData(source.row()) if source.isValid() else None

    def selectedRows(self) -> list[Any]:
        rows = sorted({index.row() for index in self._view.selectionModel().selectedRows()})
        return [self.rowData(row) for row in rows]

    def setSearchText(self, text: str) -> None:
        self._search.setText(str(text))
        self._apply_search()

    def searchText(self) -> str:
        return self._search.text()

    def _apply_search(self) -> None:
        self._filter_proxy.setSearchText("" if self._server_mode else self._search.text())
        self._reset_to_first_page()
        self._filters_updated()

    def setColumnFilter(self, key: str, value: str) -> None:
        column = next((item for item in self._model.columns if item.key == key), None)
        if column is None:
            raise KeyError(f"Unknown table column: {key!r}")
        if not column.filterable:
            raise ValueError(f"Column {key!r} is not filterable.")
        text = str(value).strip()
        if text:
            self._column_filters[str(key)] = text
        else:
            self._column_filters.pop(str(key), None)
        self._filter_proxy.setColumnFilter(key, "" if self._server_mode else text)
        self._reset_to_first_page()
        self._filters_updated()

    def columnFilters(self) -> dict[str, str]:
        return dict(self._column_filters)

    def clearFilters(self) -> None:
        self._search.clear()
        self._column_filters.clear()
        self._filter_proxy.clearFilters()
        self._reset_to_first_page()
        self._filters_updated()

    def _filters_updated(self) -> None:
        filters = {"search": self.searchText(), "columns": self.columnFilters()}
        self.filtersChanged.emit(filters)
        self._refresh_paging()
        self._emit_query()

    def setSort(self, key: str, descending: bool = False, additive: bool = False) -> None:
        column = next((i for i, item in enumerate(self._model.columns) if item.key == key), -1)
        if column < 0:
            raise KeyError(f"Unknown table column: {key!r}")
        if not self._model.columns[column].sortable:
            raise ValueError(f"Column {key!r} is not sortable.")
        order = Qt.SortOrder.DescendingOrder if descending else Qt.SortOrder.AscendingOrder
        if additive and self._multi_sort_enabled:
            self._sort_keys = [(i, o) for i, o in self._sort_keys if i != column]
            self._sort_keys.append((column, order))
        else:
            self._sort_keys = [(column, order)]
        self._filter_proxy.setSortKeys(() if self._server_mode else self._sort_keys)
        self._view.horizontalHeader().setSortIndicatorShown(True)
        self._view.horizontalHeader().setSortIndicator(column, order)
        payload = self.sortState()
        self.sortChanged.emit(payload)
        self._emit_query()

    def clearSort(self) -> None:
        self._sort_keys.clear()
        self._filter_proxy.setSortKeys(())
        self._view.horizontalHeader().setSortIndicatorShown(False)
        self.sortChanged.emit([])
        self._emit_query()

    def sortState(self) -> list[dict[str, Any]]:
        return [
            {"key": self._model.columns[column].key, "descending": order == Qt.SortOrder.DescendingOrder}
            for column, order in self._sort_keys
            if column < len(self._model.columns)
        ]

    def _header_clicked(self, column: int) -> None:
        if not self._sorting_enabled or not 0 <= column < len(self._model.columns):
            return
        current = next((order for index, order in self._sort_keys if index == column), None)
        descending = current == Qt.SortOrder.AscendingOrder
        self.setSort(self._model.columns[column].key, descending)

    def _show_header_menu(self, position: QPoint) -> None:
        column_index = self._view.horizontalHeader().logicalIndexAt(position)
        if not 0 <= column_index < len(self._model.columns):
            return
        column = self._model.columns[column_index]
        menu = QMenu(self)
        if column.sortable and self._sorting_enabled:
            ascending = menu.addAction("Sort ascending")
            descending = menu.addAction("Sort descending")
            ascending.triggered.connect(lambda: self.setSort(column.key, False))
            descending.triggered.connect(lambda: self.setSort(column.key, True))
        if column.filterable and self._filters_enabled:
            editor = QLineEdit(menu)
            editor.setPlaceholderText(f"Filter {column.title}...")
            editor.setText(self.columnFilters().get(column.key, ""))
            action = QWidgetAction(menu)
            action.setDefaultWidget(editor)
            menu.addAction(action)
            editor.returnPressed.connect(lambda: (self.setColumnFilter(column.key, editor.text()), menu.close()))
        menu.addSeparator()
        hide = menu.addAction("Hide column")
        hide.triggered.connect(lambda: self._view.setColumnHidden(column_index, True))
        clear = menu.addAction("Clear filters and sorting")
        clear.triggered.connect(lambda: (self.clearFilters(), self.clearSort()))
        menu.exec(self._view.horizontalHeader().mapToGlobal(position))

    def _rebuild_columns_menu(self) -> None:
        menu = QMenu(self._columns_button)
        for index, column in enumerate(self._model.columns):
            action = QAction(column.title, menu, checkable=True)
            action.setChecked(not self._view.isColumnHidden(index))
            action.toggled.connect(lambda visible, i=index: self._view.setColumnHidden(i, not visible))
            menu.addAction(action)
        if self._model.columns:
            menu.addSeparator()
            show_all = menu.addAction("Show all columns")
            show_all.triggered.connect(lambda: [self._view.setColumnHidden(i, False) for i in range(len(self._model.columns))])
        self._columns_button.setMenu(menu)

    def _change_page(self, page: int) -> None:
        self._page_proxy.setPage(page)
        self._refresh_summary()
        self.pageChanged.emit(page)
        self._emit_query()

    def _reset_to_first_page(self) -> None:
        self._pagination.setCurrentPage(1)
        self._page_proxy.setPage(1)

    def _refresh_paging(self, *args) -> None:
        total = self._remote_total if self._server_mode else self._filter_proxy.rowCount()
        if total:
            self._pagination.setTotalItems(total)
        else:
            self._pagination.setPageCount(1)
        current = min(self._pagination.currentPage, max(1, math.ceil(total / self.getPageSize())))
        self._pagination.setCurrentPage(current)
        self._page_proxy.setPage(current)
        self._refresh_summary()
        self._refresh_state()

    def _refresh_summary(self) -> None:
        total = self._remote_total if self._server_mode else self._filter_proxy.rowCount()
        if total <= 0:
            self._summary.setText("0 rows")
            return
        if self._pagination_enabled:
            start = (self.getCurrentPage() - 1) * self.getPageSize() + 1
            end = min(total, start + max(0, self.visibleRowCount()) - 1)
            self._summary.setText(f"{start:,}-{end:,} of {total:,} rows")
        else:
            self._summary.setText(f"{total:,} rows")

    def _refresh_state(self) -> None:
        self._state_label.setText(self._loading_text if self._loading else self._empty_text)
        visible = self._loading or self.visibleRowCount() == 0
        self._state_label.setVisible(visible)
        self._state_label.setGeometry(self._view.viewport().rect())
        self._view.setEnabled(not self._loading)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh_state()

    def _emit_query(self) -> None:
        self.queryChanged.emit({
            "page": self.getCurrentPage(),
            "pageSize": self.getPageSize(),
            "search": self.searchText(),
            "filters": self.columnFilters(),
            "sort": self.sortState(),
        })

    def _activate_index(self, index: QModelIndex) -> None:
        row = self.rowData(index.row())
        if row is not None:
            self.rowActivated.emit(row)

    def _selection_changed(self, *args) -> None:
        self.selectedRowsChanged.emit(self.selectedRows())

    def copySelection(self) -> str:
        indexes = self._view.selectionModel().selectedIndexes()
        if not indexes:
            return ""
        rows = sorted({index.row() for index in indexes})
        columns = sorted({index.column() for index in indexes})
        text = "\n".join(
            "\t".join(str(self._page_proxy.data(self._page_proxy.index(row, column)) or "") for column in columns)
            for row in rows
        )
        QApplication.clipboard().setText(text)
        return text

    def setColumnVisible(self, key: str, visible: bool) -> None:
        column = next((i for i, item in enumerate(self._model.columns) if item.key == key), -1)
        if column < 0:
            raise KeyError(f"Unknown table column: {key!r}")
        self._view.setColumnHidden(column, not bool(visible))
        self._rebuild_columns_menu()

    def saveState(self) -> dict[str, Any]:
        header = self._view.horizontalHeader()
        ordered = sorted(range(len(self._model.columns)), key=header.visualIndex)
        return {
            "columns": [
                {
                    "key": self._model.columns[index].key,
                    "width": header.sectionSize(index),
                    "visible": not self._view.isColumnHidden(index),
                }
                for index in ordered
            ],
            "search": self.searchText(),
            "filters": self.columnFilters(),
            "sort": self.sortState(),
            "pageSize": self.getPageSize(),
            "styleIndex": self._style_index,
            "densityIndex": self._density_index,
        }

    def restoreState(self, state: Mapping[str, Any]) -> None:
        header = self._view.horizontalHeader()
        indexes = {column.key: index for index, column in enumerate(self._model.columns)}
        for visual, saved in enumerate(state.get("columns", ())):
            logical = indexes.get(str(saved.get("key", "")))
            if logical is None:
                continue
            current = header.visualIndex(logical)
            if current >= 0 and current != visual:
                header.moveSection(current, min(visual, header.count() - 1))
            header.resizeSection(logical, max(24, int(saved.get("width", header.sectionSize(logical)))))
            self._view.setColumnHidden(logical, not bool(saved.get("visible", True)))
        self.setStyleIndex(int(state.get("styleIndex", self._style_index)))
        self.setDensityIndex(int(state.get("densityIndex", self._density_index)))
        self.setPageSize(int(state.get("pageSize", self.getPageSize())))
        self.setSearchText(str(state.get("search", "")))
        for key, value in dict(state.get("filters", {})).items():
            self.setColumnFilter(str(key), str(value))
        self.clearSort()
        for index, item in enumerate(state.get("sort", ())):
            self.setSort(str(item["key"]), bool(item.get("descending")), additive=index > 0)
        self._rebuild_columns_menu()

    def exportCsv(self, path: str | Path, *, filtered: bool = True) -> Path:
        target = Path(path)
        model = self._filter_proxy if filtered else self._model
        visible_columns = [i for i in range(model.columnCount()) if not self._view.isColumnHidden(i)]
        with target.open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.writer(stream)
            writer.writerow([model.headerData(i, Qt.Orientation.Horizontal) for i in visible_columns])
            for row in range(model.rowCount()):
                writer.writerow([model.data(model.index(row, i), Qt.ItemDataRole.DisplayRole) for i in visible_columns])
        return target

    def exportCsvDialog(self) -> str:
        path, _ = QFileDialog.getSaveFileName(self, "Export table", "table.csv", "CSV files (*.csv)")
        if path:
            self.exportCsv(path)
        return path

    def _apply_theme(self) -> None:
        self._surface = theme_color(self._theme, "surface")
        self._surface_alt = theme_color(self._theme, "surface_alt")
        self._header = QColor(self._surface_alt)
        self._text = theme_color(self._theme, "text")
        self._muted = theme_color(self._theme, "muted")
        self._border = theme_color(self._theme, "border")
        self._accent = theme_color(self._theme, "primary")
        self._on_accent = theme_color(self._theme, "on_primary")
        self._success = theme_color(self._theme, "success")
        self._danger = theme_color(self._theme, "danger")
        self._refresh_styles()

    def _refresh_styles(self) -> None:
        radius = theme_radius(self._theme)
        border_width = 0 if self._style_index == 2 else 1
        outer_radius = radius + 4 if self._style_index == 3 else (max(2, radius // 2) if self._style_index == 1 else radius)
        divider_width = 0 if self._style_index == 2 else 1
        row_height = (34, 42, 50)[self._density_index]
        self._view.verticalHeader().setDefaultSectionSize(row_height)
        self._view.setShowGrid(self._column_lines or self._style_index == 1)
        self._pagination.setTheme(self._theme)
        surface = color_to_css(self._surface)
        alt = color_to_css(self._surface_alt)
        header = color_to_css(self._header)
        text = color_to_css(self._text)
        muted = color_to_css(self._muted)
        border = color_to_css(self._border)
        accent = color_to_css(self._accent)
        on_accent = color_to_css(self._on_accent)
        self.setStyleSheet(f"""
            MonkezTable {{ background: {surface}; border: {border_width}px solid {border}; border-radius: {outer_radius}px; }}
            QWidget#monkezTableToolbar, QWidget#monkezTableFooter {{ background: {surface}; color: {text}; }}
            QWidget#monkezTableToolbar {{ border-bottom: {divider_width}px solid {border}; }}
            QWidget#monkezTableFooter {{ border-top: {divider_width}px solid {border}; }}
            QLineEdit#monkezTableSearch, QComboBox#monkezTablePageSize {{ background: {alt}; color: {text}; border: 1px solid {border}; border-radius: {radius}px; padding: 6px 10px; }}
            QLineEdit#monkezTableSearch:focus, QComboBox#monkezTablePageSize:focus {{ border-color: {accent}; }}
            QToolButton#monkezTableColumns {{ color: {text}; background: {alt}; border: 1px solid {border}; border-radius: {radius}px; padding: 6px 12px; }}
            QToolButton#monkezTableColumns:hover {{ border-color: {accent}; }}
            QTableView#monkezTableView {{ background: {surface}; alternate-background-color: {alt}; color: {text}; border: 0; gridline-color: {border}; outline: 0; selection-background-color: {accent}; selection-color: {on_accent}; }}
            QTableView#monkezTableView::item {{ padding: 0 9px; border-bottom: 1px solid {border if self._style_index == 1 else alt}; }}
            QTableView#monkezTableView::item:hover:!selected {{ background: {alt}; }}
            QHeaderView::section {{ background: {header}; color: {text}; border: 0; border-bottom: 1px solid {border}; padding: 8px 10px; font-weight: 600; }}
            QLabel#monkezTableState {{ color: {muted}; background: {surface}; font-size: 14px; }}
            QLabel#monkezTableSummary {{ color: {muted}; }}
        """)
        self._view.viewport().update()

    def getThemeIndex(self) -> int:
        return ThemeSupportMixin.getThemeIndex(self)

    def setThemeIndex(self, value: int) -> None:
        ThemeSupportMixin.setThemeIndex(self, value)

    def getStyleIndex(self) -> int:
        return self._style_index

    def setStyleIndex(self, value: int) -> None:
        self._style_index = min(len(self.STYLE_NAMES) - 1, max(0, int(value)))
        self._refresh_styles()

    def getDensityIndex(self) -> int:
        return self._density_index

    def setDensityIndex(self, value: int) -> None:
        self._density_index = min(len(self.DENSITY_NAMES) - 1, max(0, int(value)))
        self._refresh_styles()

    def _color_accessors(name: str):
        def getter(self):
            return QColor(getattr(self, name))

        def setter(self, value):
            color = QColor(value)
            if not color.isValid():
                raise ValueError(f"Invalid table color: {value!r}")
            setattr(self, name, color)
            self._refresh_styles()

        return getter, setter

    getBackgroundColor, setBackgroundColor = _color_accessors("_surface")
    getAlternateRowColor, setAlternateRowColor = _color_accessors("_surface_alt")
    getHeaderBackgroundColor, setHeaderBackgroundColor = _color_accessors("_header")
    getTextColor, setTextColor = _color_accessors("_text")
    getBorderColor, setBorderColor = _color_accessors("_border")
    getAccentColor, setAccentColor = _color_accessors("_accent")

    def getStyleHint(self) -> str:
        return " | ".join(f"{i} {name}" for i, name in enumerate(self.STYLE_NAMES))

    def getDensityHint(self) -> str:
        return " | ".join(f"{i} {name}" for i, name in enumerate(self.DENSITY_NAMES))

    def _ignore_hint(self, value: str) -> None:
        return None

    def getCurrentPage(self) -> int:
        return self._pagination.currentPage

    def setCurrentPage(self, value: int) -> None:
        self._pagination.setCurrentPage(value)

    def getPageSize(self) -> int:
        return self._pagination.pageSize

    def setPageSize(self, value: int) -> None:
        size = max(1, int(value))
        if size == self.getPageSize() and size == self._page_proxy._page_size:
            return
        self._pagination.setPageSize(size)
        self._page_proxy.setPageSize(size)
        if self._page_size_combo.findText(str(size)) < 0:
            self._page_size_combo.addItem(str(size))
        self._page_size_combo.setCurrentText(str(size))
        self._reset_to_first_page()
        self._refresh_paging()
        self.pageSizeChanged.emit(size)
        self._emit_query()

    def getTotalItems(self) -> int:
        return self._remote_total if self._server_mode else self._filter_proxy.rowCount()

    def setTotalItems(self, value: int) -> None:
        self._remote_total = max(0, int(value))
        self._refresh_paging()

    def getServerMode(self) -> bool:
        return self._server_mode

    def setServerMode(self, value: bool) -> None:
        self._server_mode = bool(value)
        self._filter_proxy.clearFilters()
        self._filter_proxy.setSortKeys(())
        if not self._server_mode:
            self._filter_proxy.setSearchText(self.searchText())
            for key, text in self._column_filters.items():
                self._filter_proxy.setColumnFilter(key, text)
            self._filter_proxy.setSortKeys(self._sort_keys)
        self._page_proxy.setEnabled(self._pagination_enabled and not self._server_mode)
        self._refresh_paging()
        self._emit_query()

    def getPaginationEnabled(self) -> bool:
        return self._pagination_enabled

    def setPaginationEnabled(self, value: bool) -> None:
        self._pagination_enabled = bool(value)
        self._page_proxy.setEnabled(self._pagination_enabled and not self._server_mode)
        self._pagination.setVisible(self._pagination_enabled)
        self._page_size_combo.setVisible(self._pagination_enabled)
        self._refresh_paging()

    def getLoading(self) -> bool:
        return self._loading

    def setLoading(self, value: bool) -> None:
        self._loading = bool(value)
        self._refresh_state()

    def getEditable(self) -> bool:
        return self._editable

    def setEditable(self, value: bool) -> None:
        self._editable = bool(value)
        triggers = QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed
        self._view.setEditTriggers(triggers if self._editable else QAbstractItemView.EditTrigger.NoEditTriggers)

    def _bool_property(name: str, callback=None):
        def getter(self):
            return bool(getattr(self, name))

        def setter(self, value):
            setattr(self, name, bool(value))
            if callback:
                getattr(self, callback)()

        return getter, setter

    def _update_feature_visibility(self) -> None:
        self._toolbar.setVisible(self._toolbar_visible)
        self._search.setVisible(self._search_enabled)
        self._footer.setVisible(self._footer_visible)
        self._view.horizontalHeader().setSectionsClickable(self._sorting_enabled)
        self._view.setShowGrid(self._column_lines or self._style_index == 1)
        self._view.verticalHeader().setVisible(self._row_numbers)

    getSearchEnabled, setSearchEnabled = _bool_property("_search_enabled", "_update_feature_visibility")
    getFiltersEnabled, setFiltersEnabled = _bool_property("_filters_enabled")
    getSortingEnabled, setSortingEnabled = _bool_property("_sorting_enabled", "_update_feature_visibility")
    getMultiSortEnabled, setMultiSortEnabled = _bool_property("_multi_sort_enabled")
    getRowNumbers, setRowNumbers = _bool_property("_row_numbers", "_update_feature_visibility")
    getColumnLines, setColumnLines = _bool_property("_column_lines", "_update_feature_visibility")
    getToolbarVisible, setToolbarVisible = _bool_property("_toolbar_visible", "_update_feature_visibility")
    getFooterVisible, setFooterVisible = _bool_property("_footer_visible", "_update_feature_visibility")

    def getAlternatingRows(self) -> bool:
        return self._view.alternatingRowColors()

    def setAlternatingRows(self, value: bool) -> None:
        self._view.setAlternatingRowColors(bool(value))

    def getEmptyText(self) -> str:
        return self._empty_text

    def setEmptyText(self, value: str) -> None:
        self._empty_text = str(value)
        self._refresh_state()

    def getLoadingText(self) -> str:
        return self._loading_text

    def setLoadingText(self, value: str) -> None:
        self._loading_text = str(value)
        self._refresh_state()

    themeIndex = pyqtProperty(int, getThemeIndex, setThemeIndex)
    themeHint = pyqtProperty(str, ThemeSupportMixin.getThemeOptions, ThemeSupportMixin.setThemeOptions, stored=False)
    themeName = pyqtProperty(str, ThemeSupportMixin.getThemeName, ThemeSupportMixin.setThemeName, designable=False)
    styleIndex = pyqtProperty(int, getStyleIndex, setStyleIndex)
    styleHint = pyqtProperty(str, getStyleHint, _ignore_hint, stored=False)
    densityIndex = pyqtProperty(int, getDensityIndex, setDensityIndex)
    densityHint = pyqtProperty(str, getDensityHint, _ignore_hint, stored=False)
    currentPage = pyqtProperty(int, getCurrentPage, setCurrentPage, notify=pageChanged)
    pageSize = pyqtProperty(int, getPageSize, setPageSize, notify=pageSizeChanged)
    totalItems = pyqtProperty(int, getTotalItems, setTotalItems)
    serverMode = pyqtProperty(bool, getServerMode, setServerMode)
    paginationEnabled = pyqtProperty(bool, getPaginationEnabled, setPaginationEnabled)
    searchEnabled = pyqtProperty(bool, getSearchEnabled, setSearchEnabled)
    filtersEnabled = pyqtProperty(bool, getFiltersEnabled, setFiltersEnabled)
    sortingEnabled = pyqtProperty(bool, getSortingEnabled, setSortingEnabled)
    multiSortEnabled = pyqtProperty(bool, getMultiSortEnabled, setMultiSortEnabled)
    editable = pyqtProperty(bool, getEditable, setEditable)
    alternatingRows = pyqtProperty(bool, getAlternatingRows, setAlternatingRows)
    rowNumbers = pyqtProperty(bool, getRowNumbers, setRowNumbers)
    columnLines = pyqtProperty(bool, getColumnLines, setColumnLines)
    toolbarVisible = pyqtProperty(bool, getToolbarVisible, setToolbarVisible)
    footerVisible = pyqtProperty(bool, getFooterVisible, setFooterVisible)
    loading = pyqtProperty(bool, getLoading, setLoading)
    emptyText = pyqtProperty(str, getEmptyText, setEmptyText)
    loadingText = pyqtProperty(str, getLoadingText, setLoadingText)
    backgroundColor = pyqtProperty(QColor, getBackgroundColor, setBackgroundColor)
    alternateRowColor = pyqtProperty(QColor, getAlternateRowColor, setAlternateRowColor)
    headerBackgroundColor = pyqtProperty(QColor, getHeaderBackgroundColor, setHeaderBackgroundColor)
    textColor = pyqtProperty(QColor, getTextColor, setTextColor)
    borderColor = pyqtProperty(QColor, getBorderColor, setBorderColor)
    accentColor = pyqtProperty(QColor, getAccentColor, setAccentColor)


__all__ = [
    "MonkezTable",
    "MonkezTableColumn",
    "MonkezTableModel",
    "MonkezTableFilterProxy",
    "MonkezTablePageProxy",
]
