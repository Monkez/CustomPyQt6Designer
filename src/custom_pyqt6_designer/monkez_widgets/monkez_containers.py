from __future__ import annotations

from PyQt6.QtCore import QEvent, QPointF, QRectF, Qt, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPalette, QPen
from PyQt6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QGroupBox, QScrollArea, QWidget

from .theme_support import ThemeSupportMixin
from .themes import theme_color, theme_int, theme_radius


class MonkezFrame(QFrame, ThemeSupportMixin):
    themeChanged = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._init_theme_support()
        self._background_color = QColor()
        self._border_color = QColor()
        self._radius = 8
        self._border_width = 1
        self._elevation = 0
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setMinimumSize(120, 80)
        self.setTheme("material")

    def _apply_theme(self) -> None:
        self._background_color = theme_color(self._theme, "surface")
        self._border_color = theme_color(self._theme, "border")
        self._radius = theme_int(self._theme, "radius_lg")
        self._border_width = theme_int(self._theme, "border_width")
        self._update_style()

    def _update_style(self) -> None:
        self.setStyleSheet(
            "MonkezFrame {"
            f"background-color: {self._background_color.name()};"
            f"border: {self._border_width}px solid {self._border_color.name()};"
            f"border-radius: {self._radius}px;"
            "}"
        )
        if self._elevation <= 0:
            self.setGraphicsEffect(None)
            return
        effect = self.graphicsEffect()
        if not isinstance(effect, QGraphicsDropShadowEffect):
            effect = QGraphicsDropShadowEffect(self)
            self.setGraphicsEffect(effect)
        effect.setBlurRadius(6 + self._elevation * 3)
        effect.setOffset(0, max(1, self._elevation))
        effect.setColor(theme_color(self._theme, "shadow"))

    def getBackgroundColor(self) -> QColor:
        return QColor(self._background_color)

    def setBackgroundColor(self, value: QColor) -> None:
        self._background_color = QColor(value)
        self._update_style()

    def getBorderColor(self) -> QColor:
        return QColor(self._border_color)

    def setBorderColor(self, value: QColor) -> None:
        self._border_color = QColor(value)
        self._update_style()

    def getRadius(self) -> int:
        return self._radius

    def setRadius(self, value: int) -> None:
        self._radius = max(0, int(value))
        self._update_style()

    def getBorderWidth(self) -> int:
        return self._border_width

    def setBorderWidth(self, value: int) -> None:
        self._border_width = max(0, int(value))
        self._update_style()

    def getElevation(self) -> int:
        return self._elevation

    def setElevation(self, value: int) -> None:
        self._elevation = min(12, max(0, int(value)))
        self._update_style()

    themeIndex = pyqtProperty(int, ThemeSupportMixin.getThemeIndex, ThemeSupportMixin.setThemeIndex)
    themeHint = pyqtProperty(
        str, ThemeSupportMixin.getThemeOptions, ThemeSupportMixin.setThemeOptions, stored=False
    )
    themeName = pyqtProperty(str, ThemeSupportMixin.getThemeName, ThemeSupportMixin.setThemeName, designable=False)
    backgroundColor = pyqtProperty(QColor, getBackgroundColor, setBackgroundColor)
    borderColor = pyqtProperty(QColor, getBorderColor, setBorderColor)
    radius = pyqtProperty(int, getRadius, setRadius)
    borderWidth = pyqtProperty(int, getBorderWidth, setBorderWidth)
    elevation = pyqtProperty(int, getElevation, setElevation)


class MonkezGroupBox(QGroupBox, ThemeSupportMixin):
    themeChanged = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__("Group", parent)
        self._init_theme_support()
        self._background_color = QColor()
        self._header_color = QColor()
        self._border_color = QColor()
        self._title_color = QColor()
        self._subtitle_color = QColor()
        self._accent_color = QColor()
        self._shadow_color = QColor()
        self._subtitle = ""
        self._radius = 12
        self._border_width = 1
        self._header_height = 54
        self._accent_width = 4
        self._elevation = 1
        self._content_padding = 16
        self.setMinimumSize(180, 120)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.toggled.connect(self.update)
        self.setTheme("material")

    def _apply_theme(self) -> None:
        self._background_color = theme_color(self._theme, "surface")
        self._header_color = theme_color(self._theme, "surface_alt")
        self._border_color = theme_color(self._theme, "border")
        self._title_color = theme_color(self._theme, "text")
        self._subtitle_color = theme_color(self._theme, "muted")
        self._accent_color = theme_color(self._theme, "primary")
        self._shadow_color = theme_color(self._theme, "shadow")
        self._radius = theme_int(self._theme, "radius_lg")
        self._border_width = theme_int(self._theme, "border_width")
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.WindowText, self._title_color)
        palette.setColor(QPalette.ColorRole.Text, self._title_color)
        palette.setColor(QPalette.ColorRole.ButtonText, self._title_color)
        self.setPalette(palette)
        self._update_style()

    def _update_style(self) -> None:
        self.setContentsMargins(
            self._content_padding,
            self._header_height + 10,
            self._content_padding,
            self._content_padding,
        )
        self._sync_layout_margins()
        self.update()

    def _sync_layout_margins(self) -> None:
        layout = self.layout()
        if layout is None:
            return
        layout.setContentsMargins(
            self._content_padding,
            self._header_height + 12,
            self._content_padding,
            self._content_padding,
        )

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(1.0 if self.isEnabled() else 0.58)

        card_rect = QRectF(self.rect()).adjusted(3.5, 3.5, -3.5, -3.5)
        if card_rect.width() <= 0 or card_rect.height() <= 0:
            return

        if self._elevation > 0:
            layers = min(4, self._elevation + 1)
            for layer in range(layers, 0, -1):
                shadow = QColor(self._shadow_color)
                shadow.setAlpha(max(5, shadow.alpha() // (layer + 1)))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(shadow)
                offset = layer * 0.8
                painter.drawRoundedRect(
                    card_rect.translated(0, offset),
                    self._radius + layer,
                    self._radius + layer,
                )

        card_path = QPainterPath()
        card_path.addRoundedRect(card_rect, self._radius, self._radius)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._background_color)
        painter.drawPath(card_path)

        painter.save()
        painter.setClipPath(card_path)
        header_rect = QRectF(card_rect.left(), card_rect.top(), card_rect.width(), self._header_height)
        painter.fillRect(header_rect, self._header_color)
        divider = QColor(self._border_color)
        divider.setAlpha(max(80, divider.alpha()))
        painter.setPen(QPen(divider, max(1, self._border_width)))
        painter.drawLine(
            QPointF(card_rect.left(), header_rect.bottom()),
            QPointF(card_rect.right(), header_rect.bottom()),
        )
        painter.restore()

        border = self._accent_color if self.hasFocus() else self._border_color
        border_width = max(self._border_width, 2 if self.hasFocus() else self._border_width)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(border, border_width))
        painter.drawPath(card_path)

        accent_height = max(16.0, self._header_height - 22.0)
        accent_rect = QRectF(
            card_rect.left() + 13,
            card_rect.top() + (self._header_height - accent_height) / 2,
            self._accent_width,
            accent_height,
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._accent_color)
        painter.drawRoundedRect(accent_rect, self._accent_width / 2, self._accent_width / 2)

        text_left = accent_rect.right() + 12
        if self.isCheckable():
            indicator_rect = QRectF(text_left, card_rect.top() + (self._header_height - 18) / 2, 18, 18)
            self._draw_indicator(painter, indicator_rect)
            text_left = indicator_rect.right() + 10

        text_right = card_rect.right() - 16
        text_width = max(0.0, text_right - text_left)
        title_font = QFont(self.font())
        title_font.setBold(True)
        title_font.setPointSizeF(max(9.0, title_font.pointSizeF()))
        painter.setFont(title_font)
        painter.setPen(self._title_color)

        title_metrics = painter.fontMetrics()
        title = title_metrics.elidedText(self.title(), Qt.TextElideMode.ElideRight, int(text_width))
        subtitle = self._subtitle.strip()
        if subtitle:
            title_y = card_rect.top() + 12
            painter.drawText(QRectF(text_left, title_y, text_width, 20), Qt.AlignmentFlag.AlignVCenter, title)
            subtitle_font = QFont(self.font())
            subtitle_font.setPointSizeF(max(8.0, subtitle_font.pointSizeF() - 1))
            painter.setFont(subtitle_font)
            painter.setPen(self._subtitle_color)
            subtitle_metrics = painter.fontMetrics()
            subtitle_text = subtitle_metrics.elidedText(
                subtitle,
                Qt.TextElideMode.ElideRight,
                int(text_width),
            )
            painter.drawText(
                QRectF(text_left, card_rect.top() + 31, text_width, 16),
                Qt.AlignmentFlag.AlignVCenter,
                subtitle_text,
            )
        else:
            painter.drawText(
                QRectF(text_left, card_rect.top(), text_width, self._header_height),
                Qt.AlignmentFlag.AlignVCenter,
                title,
            )

    def _draw_indicator(self, painter: QPainter, rect: QRectF) -> None:
        checked = self.isChecked()
        painter.setPen(QPen(self._accent_color if checked else self._border_color, 1.5))
        painter.setBrush(self._accent_color if checked else self._background_color)
        painter.drawRoundedRect(rect, 5, 5)
        if not checked:
            return
        painter.setPen(
            QPen(
                theme_color(self._theme, "on_primary"),
                2,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
        )
        painter.drawLine(
            QPointF(rect.left() + 4, rect.center().y()),
            QPointF(rect.left() + 8, rect.bottom() - 4),
        )
        painter.drawLine(
            QPointF(rect.left() + 8, rect.bottom() - 4),
            QPointF(rect.right() - 3, rect.top() + 4),
        )

    def mouseReleaseEvent(self, event) -> None:
        was_checked = self.isChecked()
        super().mouseReleaseEvent(event)
        if (
            self.isCheckable()
            and event.button() == Qt.MouseButton.LeftButton
            and event.position().y() <= self._header_height + 4
            and self.isChecked() == was_checked
        ):
            self.setChecked(not was_checked)

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() in {
            QEvent.Type.EnabledChange,
            QEvent.Type.FontChange,
            QEvent.Type.PaletteChange,
            QEvent.Type.StyleChange,
        }:
            self.update()

    def resizeEvent(self, event) -> None:
        self._sync_layout_margins()
        super().resizeEvent(event)

    def getBackgroundColor(self) -> QColor:
        return QColor(self._background_color)

    def setBackgroundColor(self, value: QColor) -> None:
        self._background_color = QColor(value)
        self._update_style()

    def getHeaderColor(self) -> QColor:
        return QColor(self._header_color)

    def setHeaderColor(self, value: QColor) -> None:
        self._header_color = QColor(value)
        self._update_style()

    def getBorderColor(self) -> QColor:
        return QColor(self._border_color)

    def setBorderColor(self, value: QColor) -> None:
        self._border_color = QColor(value)
        self._update_style()

    def getTitleColor(self) -> QColor:
        return QColor(self._title_color)

    def setTitleColor(self, value: QColor) -> None:
        self._title_color = QColor(value)
        self._update_style()

    def getSubtitle(self) -> str:
        return self._subtitle

    def setSubtitle(self, value: str) -> None:
        self._subtitle = value or ""
        self._update_style()

    def getSubtitleColor(self) -> QColor:
        return QColor(self._subtitle_color)

    def setSubtitleColor(self, value: QColor) -> None:
        self._subtitle_color = QColor(value)
        self._update_style()

    def getAccentColor(self) -> QColor:
        return QColor(self._accent_color)

    def setAccentColor(self, value: QColor) -> None:
        self._accent_color = QColor(value)
        self._update_style()

    def getRadius(self) -> int:
        return self._radius

    def setRadius(self, value: int) -> None:
        self._radius = max(0, int(value))
        self._update_style()

    def getBorderWidth(self) -> int:
        return self._border_width

    def setBorderWidth(self, value: int) -> None:
        self._border_width = max(0, int(value))
        self._update_style()

    def getHeaderHeight(self) -> int:
        return self._header_height

    def setHeaderHeight(self, value: int) -> None:
        self._header_height = min(96, max(40, int(value)))
        self._update_style()

    def getAccentWidth(self) -> int:
        return self._accent_width

    def setAccentWidth(self, value: int) -> None:
        self._accent_width = min(12, max(2, int(value)))
        self._update_style()

    def getElevation(self) -> int:
        return self._elevation

    def setElevation(self, value: int) -> None:
        self._elevation = min(6, max(0, int(value)))
        self._update_style()

    def getContentPadding(self) -> int:
        return self._content_padding

    def setContentPadding(self, value: int) -> None:
        self._content_padding = min(48, max(0, int(value)))
        self._update_style()

    themeIndex = pyqtProperty(int, ThemeSupportMixin.getThemeIndex, ThemeSupportMixin.setThemeIndex)
    themeHint = pyqtProperty(
        str, ThemeSupportMixin.getThemeOptions, ThemeSupportMixin.setThemeOptions, stored=False
    )
    themeName = pyqtProperty(str, ThemeSupportMixin.getThemeName, ThemeSupportMixin.setThemeName, designable=False)
    backgroundColor = pyqtProperty(QColor, getBackgroundColor, setBackgroundColor)
    headerColor = pyqtProperty(QColor, getHeaderColor, setHeaderColor)
    borderColor = pyqtProperty(QColor, getBorderColor, setBorderColor)
    titleColor = pyqtProperty(QColor, getTitleColor, setTitleColor)
    subtitle = pyqtProperty(str, getSubtitle, setSubtitle)
    subtitleColor = pyqtProperty(QColor, getSubtitleColor, setSubtitleColor)
    accentColor = pyqtProperty(QColor, getAccentColor, setAccentColor)
    radius = pyqtProperty(int, getRadius, setRadius)
    borderWidth = pyqtProperty(int, getBorderWidth, setBorderWidth)
    headerHeight = pyqtProperty(int, getHeaderHeight, setHeaderHeight)
    accentWidth = pyqtProperty(int, getAccentWidth, setAccentWidth)
    elevation = pyqtProperty(int, getElevation, setElevation)
    contentPadding = pyqtProperty(int, getContentPadding, setContentPadding)


class MonkezScrollArea(QScrollArea, ThemeSupportMixin):
    themeChanged = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._init_theme_support()
        self._background_color = QColor()
        self._border_color = QColor()
        self._scrollbar_color = QColor()
        self._scrollbar_track_color = QColor()
        self._radius = 8
        self._scrollbar_width = 10
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget(self)
        content.setObjectName("scrollAreaWidgetContents")
        content.setMinimumSize(0, 0)
        content.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWidget(content)
        self.viewport().setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setViewportMargins(1, 1, 1, 1)
        self.setMinimumSize(180, 120)
        self.setTheme("material")

    def _apply_theme(self) -> None:
        self._background_color = theme_color(self._theme, "surface")
        self._border_color = theme_color(self._theme, "border")
        self._scrollbar_color = theme_color(self._theme, "muted")
        self._scrollbar_track_color = theme_color(self._theme, "surface_alt")
        self._radius = theme_radius(self._theme)
        self._update_style()

    def _update_style(self) -> None:
        width = max(4, self._scrollbar_width)
        handle_radius = max(2, width // 2)
        self.setStyleSheet(
            "MonkezScrollArea {"
            f"background-color: {self._background_color.name()};"
            f"border: 1px solid {self._border_color.name()};"
            f"border-radius: {self._radius}px;"
            "}"
            "MonkezScrollArea > QWidget > QWidget {"
            "background-color: transparent;"
            "}"
            f"QScrollBar:vertical {{ background: {self._scrollbar_track_color.name()}; width: {width}px; margin: 0; }}"
            f"QScrollBar::handle:vertical {{ background: {self._scrollbar_color.name()}; min-height: 24px; border-radius: {handle_radius}px; }}"
            f"QScrollBar:horizontal {{ background: {self._scrollbar_track_color.name()}; height: {width}px; margin: 0; }}"
            f"QScrollBar::handle:horizontal {{ background: {self._scrollbar_color.name()}; min-width: 24px; border-radius: {handle_radius}px; }}"
            "QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }"
            "QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }"
            "QAbstractScrollArea::corner { background: transparent; }"
        )

    def getBackgroundColor(self) -> QColor:
        return QColor(self._background_color)

    def setBackgroundColor(self, value: QColor) -> None:
        self._background_color = QColor(value)
        self._update_style()

    def getBorderColor(self) -> QColor:
        return QColor(self._border_color)

    def setBorderColor(self, value: QColor) -> None:
        self._border_color = QColor(value)
        self._update_style()

    def getScrollbarColor(self) -> QColor:
        return QColor(self._scrollbar_color)

    def setScrollbarColor(self, value: QColor) -> None:
        self._scrollbar_color = QColor(value)
        self._update_style()

    def getScrollbarTrackColor(self) -> QColor:
        return QColor(self._scrollbar_track_color)

    def setScrollbarTrackColor(self, value: QColor) -> None:
        self._scrollbar_track_color = QColor(value)
        self._update_style()

    def getRadius(self) -> int:
        return self._radius

    def setRadius(self, value: int) -> None:
        self._radius = max(0, int(value))
        self._update_style()

    def getScrollbarWidth(self) -> int:
        return self._scrollbar_width

    def setScrollbarWidth(self, value: int) -> None:
        self._scrollbar_width = min(24, max(4, int(value)))
        self._update_style()

    themeIndex = pyqtProperty(int, ThemeSupportMixin.getThemeIndex, ThemeSupportMixin.setThemeIndex)
    themeHint = pyqtProperty(
        str, ThemeSupportMixin.getThemeOptions, ThemeSupportMixin.setThemeOptions, stored=False
    )
    themeName = pyqtProperty(str, ThemeSupportMixin.getThemeName, ThemeSupportMixin.setThemeName, designable=False)
    backgroundColor = pyqtProperty(QColor, getBackgroundColor, setBackgroundColor)
    borderColor = pyqtProperty(QColor, getBorderColor, setBorderColor)
    scrollbarColor = pyqtProperty(QColor, getScrollbarColor, setScrollbarColor)
    scrollbarTrackColor = pyqtProperty(QColor, getScrollbarTrackColor, setScrollbarTrackColor)
    radius = pyqtProperty(int, getRadius, setRadius)
    scrollbarWidth = pyqtProperty(int, getScrollbarWidth, setScrollbarWidth)
