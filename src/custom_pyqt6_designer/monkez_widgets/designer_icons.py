from __future__ import annotations

from functools import lru_cache

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap


INK = QColor("#17324d")
PRIMARY = QColor("#1677d2")
ACCENT = QColor("#38bdf8")
SURFACE = QColor("#f7fbff")
MUTED = QColor("#9db2c5")


@lru_cache(maxsize=None)
def designer_icon(kind: str) -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(INK, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(SURFACE)

    draw = _DRAWERS.get(kind, _draw_widget)
    draw(painter)
    painter.end()
    return QIcon(pixmap)


def _rounded_box(painter: QPainter, rect: QRectF = QRectF(8, 12, 48, 40), radius: float = 8) -> None:
    painter.drawRoundedRect(rect, radius, radius)


def _draw_widget(painter: QPainter) -> None:
    _rounded_box(painter)
    painter.setPen(QPen(PRIMARY, 4))
    painter.drawLine(18, 26, 46, 26)
    painter.drawLine(18, 37, 39, 37)


def _draw_button(painter: QPainter) -> None:
    painter.setBrush(PRIMARY)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(QRectF(7, 17, 50, 30), 8, 8)
    painter.setPen(QPen(Qt.GlobalColor.white, 3))
    painter.drawLine(21, 32, 43, 32)


def _draw_checkbox(painter: QPainter) -> None:
    painter.setBrush(SURFACE)
    painter.drawRoundedRect(QRectF(10, 18, 26, 26), 5, 5)
    painter.setPen(QPen(PRIMARY, 4))
    painter.drawLine(16, 31, 23, 38)
    painter.drawLine(23, 38, 34, 24)
    painter.setPen(QPen(INK, 3))
    painter.drawLine(43, 25, 55, 25)
    painter.drawLine(43, 36, 53, 36)


def _draw_radio(painter: QPainter) -> None:
    painter.drawEllipse(QRectF(10, 18, 26, 26))
    painter.setBrush(PRIMARY)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(QRectF(17, 25, 12, 12))
    painter.setPen(QPen(INK, 3))
    painter.drawLine(43, 25, 55, 25)
    painter.drawLine(43, 36, 53, 36)


def _draw_combo(painter: QPainter) -> None:
    _rounded_box(painter, QRectF(6, 15, 52, 34), 8)
    painter.drawLine(42, 15, 42, 49)
    painter.setPen(QPen(PRIMARY, 3))
    painter.drawLine(47, 28, 51, 33)
    painter.drawLine(51, 33, 55, 28)


def _draw_text(painter: QPainter) -> None:
    _rounded_box(painter, QRectF(6, 15, 52, 34), 7)
    painter.setPen(QPen(PRIMARY, 3))
    painter.drawLine(16, 25, 16, 39)
    painter.drawLine(12, 25, 20, 25)
    painter.drawLine(12, 39, 20, 39)
    painter.setPen(QPen(MUTED, 3))
    painter.drawLine(27, 32, 50, 32)


def _draw_switch(painter: QPainter) -> None:
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(PRIMARY)
    painter.drawRoundedRect(QRectF(7, 20, 50, 24), 12, 12)
    painter.setBrush(Qt.GlobalColor.white)
    painter.drawEllipse(QRectF(36, 23, 18, 18))


def _draw_slider(painter: QPainter) -> None:
    painter.setPen(QPen(MUTED, 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(8, 32, 56, 32)
    painter.setPen(QPen(PRIMARY, 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(8, 32, 34, 32)
    painter.setPen(QPen(PRIMARY, 3))
    painter.setBrush(SURFACE)
    painter.drawEllipse(QRectF(27, 25, 14, 14))


def _draw_progress(painter: QPainter) -> None:
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#dcecf8"))
    painter.drawRoundedRect(QRectF(6, 25, 52, 14), 7, 7)
    painter.setBrush(PRIMARY)
    painter.drawRoundedRect(QRectF(6, 25, 34, 14), 7, 7)


def _draw_image(painter: QPainter) -> None:
    _rounded_box(painter, QRectF(8, 10, 48, 44), 5)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#f8c55b"))
    painter.drawEllipse(QRectF(39, 17, 9, 9))
    path = QPainterPath()
    path.moveTo(12, 48)
    path.lineTo(25, 31)
    path.lineTo(34, 40)
    path.lineTo(41, 32)
    path.lineTo(53, 48)
    path.closeSubpath()
    painter.setBrush(PRIMARY)
    painter.drawPath(path)


def _draw_camera(painter: QPainter) -> None:
    painter.setBrush(SURFACE)
    painter.drawRoundedRect(QRectF(7, 20, 50, 31), 6, 6)
    painter.drawRoundedRect(QRectF(18, 13, 18, 9), 3, 3)
    painter.setBrush(PRIMARY)
    painter.drawEllipse(QRectF(23, 26, 18, 18))
    painter.setBrush(SURFACE)
    painter.drawEllipse(QRectF(28, 31, 8, 8))


def _draw_frame(painter: QPainter) -> None:
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(QRectF(8, 10, 48, 44), 7, 7)
    painter.setPen(QPen(PRIMARY, 2, Qt.PenStyle.DashLine))
    painter.drawRoundedRect(QRectF(15, 17, 34, 30), 4, 4)


def _draw_group(painter: QPainter) -> None:
    painter.setBrush(SURFACE)
    painter.drawRoundedRect(QRectF(8, 16, 48, 38), 7, 7)
    painter.setBrush(SURFACE)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRect(QRectF(15, 11, 25, 11))
    painter.setPen(QPen(PRIMARY, 3))
    painter.drawLine(18, 17, 37, 17)


def _draw_scroll(painter: QPainter) -> None:
    _rounded_box(painter, QRectF(8, 8, 48, 48), 6)
    painter.setPen(QPen(MUTED, 3))
    painter.drawLine(17, 20, 43, 20)
    painter.drawLine(17, 31, 40, 31)
    painter.drawLine(17, 42, 36, 42)
    painter.setPen(QPen(PRIMARY, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(50, 17, 50, 39)


def _draw_spin(painter: QPainter) -> None:
    _rounded_box(painter, QRectF(7, 15, 50, 34), 6)
    painter.drawLine(42, 15, 42, 49)
    painter.setPen(QPen(PRIMARY, 3))
    painter.drawLine(47, 26, 51, 22)
    painter.drawLine(51, 22, 55, 26)
    painter.drawLine(47, 38, 51, 42)
    painter.drawLine(51, 42, 55, 38)
    painter.setPen(QPen(INK, 3))
    painter.drawLine(16, 32, 32, 32)


def _draw_dial(painter: QPainter) -> None:
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(MUTED, 7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawArc(QRectF(12, 12, 40, 40), 225 * 16, -270 * 16)
    painter.setPen(QPen(PRIMARY, 7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawArc(QRectF(12, 12, 40, 40), 225 * 16, -150 * 16)
    painter.setPen(QPen(PRIMARY, 3))
    painter.setBrush(SURFACE)
    painter.drawEllipse(QRectF(43, 16, 10, 10))


def _draw_calendar(painter: QPainter) -> None:
    _rounded_box(painter, QRectF(9, 11, 46, 44), 6)
    painter.setBrush(PRIMARY)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(QRectF(9, 11, 46, 13), 6, 6)
    painter.drawRect(QRectF(9, 18, 46, 7))
    painter.setBrush(INK)
    for y in (32, 43):
        for x in (19, 32, 45):
            painter.drawEllipse(QPointF(x, y), 2.3, 2.3)


def _draw_date(painter: QPainter) -> None:
    _draw_calendar(painter)
    painter.setBrush(PRIMARY)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(QPointF(45, 43), 5, 5)


def _draw_time(painter: QPainter) -> None:
    painter.drawEllipse(QRectF(10, 10, 44, 44))
    painter.setPen(QPen(PRIMARY, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(32, 32, 32, 19)
    painter.drawLine(32, 32, 43, 37)


def _draw_datetime(painter: QPainter) -> None:
    _draw_calendar(painter)
    painter.setPen(QPen(PRIMARY, 3))
    painter.setBrush(SURFACE)
    painter.drawEllipse(QRectF(35, 34, 20, 20))
    painter.drawLine(45, 44, 45, 38)
    painter.drawLine(45, 44, 50, 47)


def _draw_lcd(painter: QPainter) -> None:
    painter.setBrush(QColor("#10273a"))
    painter.drawRoundedRect(QRectF(7, 16, 50, 32), 5, 5)
    painter.setPen(QPen(ACCENT, 3))
    painter.drawLine(16, 25, 24, 25)
    painter.drawLine(24, 25, 24, 39)
    painter.drawLine(16, 39, 24, 39)
    painter.drawLine(34, 25, 42, 25)
    painter.drawLine(34, 32, 42, 32)
    painter.drawLine(34, 39, 42, 39)
    painter.drawLine(42, 25, 42, 39)


_DRAWERS = {
    "button": _draw_button,
    "checkbox": _draw_checkbox,
    "combobox": _draw_combo,
    "image": _draw_image,
    "progress": _draw_progress,
    "radio": _draw_radio,
    "slider": _draw_slider,
    "switch": _draw_switch,
    "textinput": _draw_text,
    "camera": _draw_camera,
    "frame": _draw_frame,
    "groupbox": _draw_group,
    "scrollarea": _draw_scroll,
    "spinbox": _draw_spin,
    "doublespinbox": _draw_spin,
    "dial": _draw_dial,
    "dateedit": _draw_date,
    "timeedit": _draw_time,
    "datetimeedit": _draw_datetime,
    "calendar": _draw_calendar,
    "lcd": _draw_lcd,
}
