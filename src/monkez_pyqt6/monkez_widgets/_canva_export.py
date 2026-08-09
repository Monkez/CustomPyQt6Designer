"""Native scene/selection export pipeline for :class:`MonkezCanva`."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping

from PyQt6.QtCore import QMarginsF, QRect, QRectF, QSize, Qt
from PyQt6.QtGui import (
    QImage,
    QImageWriter,
    QPageLayout,
    QPageSize,
    QPainter,
    QPdfWriter,
)
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtSvg import QSvgGenerator

from monkez_pyqt6.monkez_canva.exchange import (
    CanvasPageConfig,
    normalize_page_config,
    select_graph,
)


GRAPHIC_EXPORT_FORMATS = ("png", "svg", "pdf")
GRAPHIC_EXPORT_SCOPES = ("scene", "selection")


_PAGE_SIZES = {
    "A3": QPageSize.PageSizeId.A3,
    "A4": QPageSize.PageSizeId.A4,
    "A5": QPageSize.PageSizeId.A5,
    "LETTER": QPageSize.PageSizeId.Letter,
    "LEGAL": QPageSize.PageSizeId.Legal,
}


def normalize_graphic_format(path: str | Path, format_name: str = "") -> str:
    result = str(format_name).lower().strip().lstrip(".") or Path(path).suffix.lower().lstrip(".")
    if result not in GRAPHIC_EXPORT_FORMATS:
        raise ValueError(f"Unsupported MonkezCanva graphic export format: {result or '<none>'}")
    return result


def normalize_export_scope(scope: str) -> str:
    result = str(scope).lower().strip()
    if result not in GRAPHIC_EXPORT_SCOPES:
        raise ValueError(f"Unsupported MonkezCanva export scope: {scope}")
    return result


def configure_paged_device(device: QPdfWriter | QPrinter, config: CanvasPageConfig) -> None:
    device.setResolution(config.resolution)
    layout = QPageLayout(
        QPageSize(_PAGE_SIZES[config.size]),
        (QPageLayout.Orientation.Landscape if config.orientation == "landscape" else QPageLayout.Orientation.Portrait),
        QMarginsF(
            config.margin_left_mm,
            config.margin_top_mm,
            config.margin_right_mm,
            config.margin_bottom_mm,
        ),
        QPageLayout.Unit.Millimeter,
    )
    device.setPageLayout(layout)


def _object_items(canvas) -> dict[str, Any]:
    return {
        **canvas._groups,
        **canvas._connectors,
        **canvas._elements,
    }


def export_object_ids(canvas, scope: str) -> frozenset[str]:
    normalized = normalize_export_scope(scope)
    if normalized == "scene":
        return frozenset(_object_items(canvas))
    requested = canvas.selectedObjectIds()
    if not requested:
        raise ValueError("Select at least one canvas object before exporting the selection")
    resolved = select_graph(canvas.documentModel(), requested)
    return resolved.object_ids


@contextmanager
def export_render_state(canvas, scope: str, *, transparent: bool) -> Iterator[tuple[QRectF, frozenset[str]]]:
    """Hide editor artifacts/excluded objects and restore every state afterward."""

    object_items = _object_items(canvas)
    included = export_object_ids(canvas, scope)
    visibility = {object_id: item.isVisible() for object_id, item in object_items.items()}
    selection = {object_id: item.isSelected() for object_id, item in object_items.items()}
    suppress_background = bool(getattr(canvas._scene, "_suppress_export_background", False))
    force_quality = bool(getattr(canvas, "_force_quality_render", False))
    guides = canvas._scene._smart_guides
    try:
        canvas._scene._smart_guides = ()
        canvas._scene._suppress_export_background = bool(transparent)
        canvas._force_quality_render = True
        for object_id, item in object_items.items():
            item.setSelected(False)
            if object_id not in included:
                item.setVisible(False)
        visible_items = [item for object_id, item in object_items.items() if object_id in included and item.isVisible()]
        if not visible_items:
            raise ValueError("The requested export scope contains no visible canvas objects")
        bounds = visible_items[0].sceneBoundingRect()
        for item in visible_items[1:]:
            bounds = bounds.united(item.sceneBoundingRect())
        yield bounds, included
    finally:
        canvas._scene._suppress_export_background = suppress_background
        canvas._force_quality_render = force_quality
        canvas._scene._smart_guides = guides
        for object_id, item in object_items.items():
            item.setVisible(visibility[object_id])
            item.setSelected(selection[object_id])
        canvas._scene.update()


def _padded(bounds: QRectF, padding: float) -> QRectF:
    pad = max(0.0, float(padding))
    return bounds.adjusted(-pad, -pad, pad, pad)


def _render_scene(canvas, painter: QPainter, target: QRectF, source: QRectF) -> None:
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    canvas._scene.render(
        painter,
        target,
        source,
        Qt.AspectRatioMode.KeepAspectRatio,
    )


def export_graphic(
    canvas,
    path: str | Path,
    *,
    scope: str = "scene",
    format_name: str = "",
    transparent: bool = False,
    padding: float = 24.0,
    scale: float = 1.0,
    page_config: CanvasPageConfig | Mapping[str, Any] | None = None,
) -> Path:
    """Export the scene or current selection to PNG, SVG or PDF."""

    target_path = Path(path).expanduser().resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    format_key = normalize_graphic_format(target_path, format_name)
    normalized_scope = normalize_export_scope(scope)
    factor = max(0.1, min(8.0, float(scale)))
    with export_render_state(canvas, normalized_scope, transparent=transparent) as (bounds, _ids):
        source = _padded(bounds, padding)
        if format_key == "png":
            size = QSize(
                max(1, round(source.width() * factor)),
                max(1, round(source.height() * factor)),
            )
            image_format = QImage.Format.Format_ARGB32_Premultiplied
            image = QImage(size, image_format)
            image.fill(Qt.GlobalColor.transparent if transparent else canvas.backgroundColor)
            painter = QPainter(image)
            _render_scene(canvas, painter, QRectF(0, 0, size.width(), size.height()), source)
            painter.end()
            writer = QImageWriter(str(target_path), b"png")
            writer.setCompression(6)
            if not writer.write(image):
                raise OSError(f"Could not write PNG export: {writer.errorString()}")
        elif format_key == "svg":
            size = QSize(
                max(1, round(source.width() * factor)),
                max(1, round(source.height() * factor)),
            )
            generator = QSvgGenerator()
            generator.setFileName(str(target_path))
            generator.setSize(size)
            generator.setViewBox(QRect(0, 0, size.width(), size.height()))
            generator.setTitle("MonkezCanva export")
            generator.setDescription(f"{normalized_scope} export")
            painter = QPainter(generator)
            _render_scene(canvas, painter, QRectF(0, 0, size.width(), size.height()), source)
            painter.end()
        else:
            config = normalize_page_config(page_config)
            writer = QPdfWriter(str(target_path))
            writer.setTitle("MonkezCanva export")
            configure_paged_device(writer, config)
            painter = QPainter(writer)
            paint_rect = QRectF(writer.pageLayout().paintRectPixels(writer.resolution()))
            _render_scene(canvas, painter, paint_rect, source)
            painter.end()
    if not target_path.is_file() or target_path.stat().st_size <= 0:
        raise OSError(f"MonkezCanva export did not produce a file: {target_path}")
    return target_path


def print_canvas(
    canvas,
    printer: QPrinter,
    *,
    scope: str = "scene",
    page_config: CanvasPageConfig | Mapping[str, Any] | None = None,
) -> None:
    """Render a canvas scope onto an already configured printer."""

    config = normalize_page_config(page_config)
    configure_paged_device(printer, config)
    with export_render_state(canvas, scope, transparent=False) as (bounds, _ids):
        painter = QPainter(printer)
        paint_rect = QRectF(printer.pageLayout().paintRectPixels(printer.resolution()))
        _render_scene(canvas, painter, paint_rect, _padded(bounds, 24.0))
        painter.end()
