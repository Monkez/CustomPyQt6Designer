from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QAbstractSlider

from .shadow_support import ShadowSupportMixin
from .theme_support import ThemeSupportMixin
from .themes import theme_color


class _GaugeBase(QAbstractSlider, ThemeSupportMixin, ShadowSupportMixin):
    themeChanged = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._init_theme_support()
        self._init_shadow_support()
        self._track_color = QColor()
        self._value_color = QColor()
        self._text_color = QColor()
        self._muted_color = QColor()
        self._warning_color = QColor()
        self._danger_color = QColor()
        self._label = "VALUE"
        self._suffix = "%"
        self._show_value = True
        self._show_label = True
        self.setRange(0, 100)
        self.setValue(68)
        self.setTheme("material")

    def _apply_theme(self) -> None:
        self._track_color = theme_color(self._theme, "surface_alt")
        self._value_color = theme_color(self._theme, "primary")
        self._text_color = theme_color(self._theme, "text")
        self._muted_color = theme_color(self._theme, "muted")
        self._warning_color = theme_color(self._theme, "warning")
        self._danger_color = theme_color(self._theme, "danger")
        self.update()

    def _ratio(self) -> float:
        return (self.value() - self.minimum()) / max(1, self.maximum() - self.minimum())

    def _value_text(self) -> str:
        return f"{self.value()}{self._suffix}"

    def getLabel(self) -> str:
        return self._label

    def setLabel(self, value: str) -> None:
        self._label = value or ""
        self.update()

    def getSuffix(self) -> str:
        return self._suffix

    def setSuffix(self, value: str) -> None:
        self._suffix = value or ""
        self.update()

    def getShowValue(self) -> bool:
        return self._show_value

    def setShowValue(self, value: bool) -> None:
        self._show_value = bool(value)
        self.update()

    def getShowLabel(self) -> bool:
        return self._show_label

    def setShowLabel(self, value: bool) -> None:
        self._show_label = bool(value)
        self.update()

    def _color_accessors(name):
        def getter(self):
            return QColor(getattr(self, name))

        def setter(self, value):
            setattr(self, name, QColor(value))
            self.update()

        return getter, setter

    getTrackColor, setTrackColor = _color_accessors("_track_color")
    getValueColor, setValueColor = _color_accessors("_value_color")
    getTextColor, setTextColor = _color_accessors("_text_color")
    getWarningColor, setWarningColor = _color_accessors("_warning_color")
    getDangerColor, setDangerColor = _color_accessors("_danger_color")


def _declare_gauge_properties(namespace: dict) -> None:
    namespace["themeIndex"] = pyqtProperty(int, ThemeSupportMixin.getThemeIndex, ThemeSupportMixin.setThemeIndex)
    namespace["themeHint"] = pyqtProperty(
        str, ThemeSupportMixin.getThemeOptions, ThemeSupportMixin.setThemeOptions, stored=False
    )
    namespace["label"] = pyqtProperty(str, _GaugeBase.getLabel, _GaugeBase.setLabel)
    namespace["suffix"] = pyqtProperty(str, _GaugeBase.getSuffix, _GaugeBase.setSuffix)
    namespace["showValue"] = pyqtProperty(bool, _GaugeBase.getShowValue, _GaugeBase.setShowValue)
    namespace["showLabel"] = pyqtProperty(bool, _GaugeBase.getShowLabel, _GaugeBase.setShowLabel)
    namespace["trackColor"] = pyqtProperty(QColor, _GaugeBase.getTrackColor, _GaugeBase.setTrackColor)
    namespace["valueColor"] = pyqtProperty(QColor, _GaugeBase.getValueColor, _GaugeBase.setValueColor)
    namespace["textColor"] = pyqtProperty(QColor, _GaugeBase.getTextColor, _GaugeBase.setTextColor)
    namespace["warningColor"] = pyqtProperty(QColor, _GaugeBase.getWarningColor, _GaugeBase.setWarningColor)
    namespace["dangerColor"] = pyqtProperty(QColor, _GaugeBase.getDangerColor, _GaugeBase.setDangerColor)
    namespace["shadowEnabled"] = pyqtProperty(
        bool, ShadowSupportMixin.getShadowEnabled, ShadowSupportMixin.setShadowEnabled
    )
    namespace["shadowBlur"] = pyqtProperty(int, ShadowSupportMixin.getShadowBlur, ShadowSupportMixin.setShadowBlur)
    namespace["shadowOffsetX"] = pyqtProperty(
        int, ShadowSupportMixin.getShadowOffsetX, ShadowSupportMixin.setShadowOffsetX
    )
    namespace["shadowOffsetY"] = pyqtProperty(
        int, ShadowSupportMixin.getShadowOffsetY, ShadowSupportMixin.setShadowOffsetY
    )
    namespace["shadowColor"] = pyqtProperty(
        QColor, ShadowSupportMixin.getShadowColor, ShadowSupportMixin.setShadowColor
    )


class MonkezRadialGauge(_GaugeBase):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._major_ticks = 10
        self._minor_ticks = 4
        self._show_needle = True
        self._show_scale_labels = True
        self._start_angle = 225
        self._span_angle = 270
        self.setMinimumSize(180, 180)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(self.width(), self.height())
        center = QPointF(self.width() / 2, self.height() / 2)
        radius = side * 0.39
        ratio = self._ratio()

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(theme_color(self._theme, "surface"))
        painter.drawEllipse(center, side * 0.46, side * 0.46)

        total_ticks = self._major_ticks * (self._minor_ticks + 1)
        for index in range(total_ticks + 1):
            tick_ratio = index / total_ticks
            angle = math.radians(self._start_angle - tick_ratio * self._span_angle)
            major = index % (self._minor_ticks + 1) == 0
            outer = radius
            inner = radius - (13 if major else 6)
            color = self._value_color if tick_ratio <= ratio else self._track_color
            painter.setPen(QPen(color, 2.5 if major else 1, cap=Qt.PenCapStyle.RoundCap))
            painter.drawLine(
                QPointF(center.x() + inner * math.cos(angle), center.y() - inner * math.sin(angle)),
                QPointF(center.x() + outer * math.cos(angle), center.y() - outer * math.sin(angle)),
            )

        if self._show_scale_labels:
            painter.setPen(self._muted_color)
            font = QFont(self.font())
            font.setPointSizeF(max(7, side / 38))
            painter.setFont(font)
            for index in range(self._major_ticks + 1):
                tick_ratio = index / self._major_ticks
                angle = math.radians(self._start_angle - tick_ratio * self._span_angle)
                label_radius = radius - 27
                value = round(self.minimum() + tick_ratio * (self.maximum() - self.minimum()))
                point = QPointF(
                    center.x() + label_radius * math.cos(angle),
                    center.y() - label_radius * math.sin(angle),
                )
                painter.drawText(QRectF(point.x() - 18, point.y() - 9, 36, 18), Qt.AlignmentFlag.AlignCenter, str(value))

        needle_angle = math.radians(self._start_angle - ratio * self._span_angle)
        if self._show_needle:
            end = QPointF(
                center.x() + radius * 0.67 * math.cos(needle_angle),
                center.y() - radius * 0.67 * math.sin(needle_angle),
            )
            painter.setPen(QPen(self._danger_color, 3, cap=Qt.PenCapStyle.RoundCap))
            painter.drawLine(center, end)
            painter.setBrush(self._danger_color)
            painter.setPen(QPen(theme_color(self._theme, "surface"), 3))
            painter.drawEllipse(center, 8, 8)

        self._draw_center_text(painter, side)

    def _draw_center_text(self, painter, side) -> None:
        if self._show_value:
            font = QFont(self.font())
            font.setBold(True)
            font.setPointSizeF(max(12, side / 15))
            painter.setFont(font)
            painter.setPen(self._text_color)
            painter.drawText(QRectF(0, self.height() * 0.56, self.width(), 34), Qt.AlignmentFlag.AlignCenter, self._value_text())
        if self._show_label:
            painter.setPen(self._muted_color)
            font = QFont(self.font())
            font.setPointSizeF(max(7, side / 28))
            font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2)
            painter.setFont(font)
            painter.drawText(QRectF(0, self.height() * 0.72, self.width(), 24), Qt.AlignmentFlag.AlignCenter, self._label.upper())

    def getMajorTicks(self) -> int:
        return self._major_ticks

    def setMajorTicks(self, value: int) -> None:
        self._major_ticks = min(20, max(2, int(value)))
        self.update()

    def getMinorTicks(self) -> int:
        return self._minor_ticks

    def setMinorTicks(self, value: int) -> None:
        self._minor_ticks = min(10, max(0, int(value)))
        self.update()

    def getShowNeedle(self) -> bool:
        return self._show_needle

    def setShowNeedle(self, value: bool) -> None:
        self._show_needle = bool(value)
        self.update()

    def getShowScaleLabels(self) -> bool:
        return self._show_scale_labels

    def setShowScaleLabels(self, value: bool) -> None:
        self._show_scale_labels = bool(value)
        self.update()

    _declare_gauge_properties(locals())
    majorTicks = pyqtProperty(int, getMajorTicks, setMajorTicks)
    minorTicks = pyqtProperty(int, getMinorTicks, setMinorTicks)
    showNeedle = pyqtProperty(bool, getShowNeedle, setShowNeedle)
    showScaleLabels = pyqtProperty(bool, getShowScaleLabels, setShowScaleLabels)


class MonkezArcGauge(_GaugeBase):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._arc_width = 18
        self._warning_threshold = 70
        self._danger_threshold = 90
        self._segmented = False
        self._segment_count = 24
        self.setMinimumSize(180, 130)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(self.width(), self.height() * 1.45)
        rect = QRectF((self.width() - side) / 2 + 14, 14, side - 28, side - 28)
        ratio = self._ratio()
        color = self._value_color
        if self.value() >= self._danger_threshold:
            color = self._danger_color
        elif self.value() >= self._warning_threshold:
            color = self._warning_color

        if self._segmented:
            for index in range(self._segment_count):
                segment_ratio = index / max(1, self._segment_count - 1)
                painter.setPen(QPen(color if segment_ratio <= ratio else self._track_color, self._arc_width,
                                    cap=Qt.PenCapStyle.RoundCap))
                painter.drawArc(rect, int((210 - segment_ratio * 240) * 16), -5 * 16)
        else:
            painter.setPen(QPen(self._track_color, self._arc_width, cap=Qt.PenCapStyle.RoundCap))
            painter.drawArc(rect, 210 * 16, -240 * 16)
            painter.setPen(QPen(color, self._arc_width, cap=Qt.PenCapStyle.RoundCap))
            painter.drawArc(rect, 210 * 16, int(-240 * 16 * ratio))

        if self._show_value:
            font = QFont(self.font())
            font.setBold(True)
            font.setPointSizeF(max(16, min(self.width(), self.height()) / 6))
            painter.setFont(font)
            painter.setPen(self._text_color)
            painter.drawText(QRectF(0, self.height() * 0.35, self.width(), 42), Qt.AlignmentFlag.AlignCenter, self._value_text())
        if self._show_label:
            painter.setPen(self._muted_color)
            label_font = QFont(self.font())
            label_font.setPointSizeF(max(8, min(self.width(), self.height()) / 12))
            label_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.8)
            painter.setFont(label_font)
            painter.drawText(QRectF(0, self.height() * 0.68, self.width(), 24), Qt.AlignmentFlag.AlignCenter, self._label)

    def getArcWidth(self) -> int:
        return self._arc_width

    def setArcWidth(self, value: int) -> None:
        self._arc_width = min(48, max(4, int(value)))
        self.update()

    def getWarningThreshold(self) -> int:
        return self._warning_threshold

    def setWarningThreshold(self, value: int) -> None:
        self._warning_threshold = int(value)
        self.update()

    def getDangerThreshold(self) -> int:
        return self._danger_threshold

    def setDangerThreshold(self, value: int) -> None:
        self._danger_threshold = int(value)
        self.update()

    def getSegmented(self) -> bool:
        return self._segmented

    def setSegmented(self, value: bool) -> None:
        self._segmented = bool(value)
        self.update()

    def getSegmentCount(self) -> int:
        return self._segment_count

    def setSegmentCount(self, value: int) -> None:
        self._segment_count = min(80, max(6, int(value)))
        self.update()

    _declare_gauge_properties(locals())
    arcWidth = pyqtProperty(int, getArcWidth, setArcWidth)
    warningThreshold = pyqtProperty(int, getWarningThreshold, setWarningThreshold)
    dangerThreshold = pyqtProperty(int, getDangerThreshold, setDangerThreshold)
    segmented = pyqtProperty(bool, getSegmented, setSegmented)
    segmentCount = pyqtProperty(int, getSegmentCount, setSegmentCount)


class MonkezLinearGauge(_GaugeBase):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._vertical = False
        self._bar_thickness = 18
        self._target_value = 82
        self._show_target = True
        self._rounded = True
        self.setMinimumSize(240, 80)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        ratio = self._ratio()
        if self._vertical:
            track = QRectF(self.width() * 0.42, 16, self._bar_thickness, self.height() - 32)
            value_rect = QRectF(track.left(), track.bottom() - track.height() * ratio, track.width(), track.height() * ratio)
        else:
            track = QRectF(18, self.height() * 0.52, self.width() - 36, self._bar_thickness)
            value_rect = QRectF(track.left(), track.top(), track.width() * ratio, track.height())
        radius = self._bar_thickness / 2 if self._rounded else 2
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._track_color)
        painter.drawRoundedRect(track, radius, radius)
        painter.setBrush(self._value_color)
        painter.drawRoundedRect(value_rect, radius, radius)

        if self._show_target:
            target_ratio = (self._target_value - self.minimum()) / max(1, self.maximum() - self.minimum())
            painter.setPen(QPen(self._warning_color, 3, cap=Qt.PenCapStyle.RoundCap))
            if self._vertical:
                y = track.bottom() - track.height() * target_ratio
                painter.drawLine(QPointF(track.left() - 8, y), QPointF(track.right() + 8, y))
            else:
                x = track.left() + track.width() * target_ratio
                painter.drawLine(QPointF(x, track.top() - 8), QPointF(x, track.bottom() + 8))

        if self._show_label:
            painter.setPen(self._muted_color)
            painter.drawText(QRectF(18, 8, self.width() - 36, 24), Qt.AlignmentFlag.AlignLeft, self._label)
        if self._show_value:
            font = QFont(self.font())
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(self._text_color)
            painter.drawText(QRectF(18, 8, self.width() - 36, 24), Qt.AlignmentFlag.AlignRight, self._value_text())

    def getVertical(self) -> bool:
        return self._vertical

    def setVertical(self, value: bool) -> None:
        self._vertical = bool(value)
        self.updateGeometry()
        self.update()

    def getBarThickness(self) -> int:
        return self._bar_thickness

    def setBarThickness(self, value: int) -> None:
        self._bar_thickness = min(60, max(4, int(value)))
        self.update()

    def getTargetValue(self) -> int:
        return self._target_value

    def setTargetValue(self, value: int) -> None:
        self._target_value = int(value)
        self.update()

    def getShowTarget(self) -> bool:
        return self._show_target

    def setShowTarget(self, value: bool) -> None:
        self._show_target = bool(value)
        self.update()

    def getRounded(self) -> bool:
        return self._rounded

    def setRounded(self, value: bool) -> None:
        self._rounded = bool(value)
        self.update()

    _declare_gauge_properties(locals())
    vertical = pyqtProperty(bool, getVertical, setVertical)
    barThickness = pyqtProperty(int, getBarThickness, setBarThickness)
    targetValue = pyqtProperty(int, getTargetValue, setTargetValue)
    showTarget = pyqtProperty(bool, getShowTarget, setShowTarget)
    rounded = pyqtProperty(bool, getRounded, setRounded)
