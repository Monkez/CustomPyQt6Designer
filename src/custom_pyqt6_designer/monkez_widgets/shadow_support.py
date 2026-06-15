from __future__ import annotations

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGraphicsDropShadowEffect


class ShadowSupportMixin:
    def _init_shadow_support(self) -> None:
        self._shadow_enabled = False
        self._shadow_blur = 18
        self._shadow_offset_x = 0
        self._shadow_offset_y = 4
        self._shadow_color = QColor(0, 0, 0, 70)

    def _apply_shadow(self) -> None:
        if not self._shadow_enabled:
            self.setGraphicsEffect(None)
            return
        effect = self.graphicsEffect()
        if not isinstance(effect, QGraphicsDropShadowEffect):
            effect = QGraphicsDropShadowEffect(self)
            self.setGraphicsEffect(effect)
        effect.setBlurRadius(self._shadow_blur)
        effect.setOffset(self._shadow_offset_x, self._shadow_offset_y)
        effect.setColor(self._shadow_color)

    def getShadowEnabled(self) -> bool:
        return self._shadow_enabled

    def setShadowEnabled(self, value: bool) -> None:
        self._shadow_enabled = bool(value)
        self._apply_shadow()

    def getShadowBlur(self) -> int:
        return self._shadow_blur

    def setShadowBlur(self, value: int) -> None:
        self._shadow_blur = min(80, max(0, int(value)))
        self._apply_shadow()

    def getShadowOffsetX(self) -> int:
        return self._shadow_offset_x

    def setShadowOffsetX(self, value: int) -> None:
        self._shadow_offset_x = min(40, max(-40, int(value)))
        self._apply_shadow()

    def getShadowOffsetY(self) -> int:
        return self._shadow_offset_y

    def setShadowOffsetY(self, value: int) -> None:
        self._shadow_offset_y = min(40, max(-40, int(value)))
        self._apply_shadow()

    def getShadowColor(self) -> QColor:
        return QColor(self._shadow_color)

    def setShadowColor(self, value: QColor) -> None:
        self._shadow_color = QColor(value)
        self._apply_shadow()
