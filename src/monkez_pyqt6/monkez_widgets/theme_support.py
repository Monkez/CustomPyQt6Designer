from __future__ import annotations

from .themes import normalize_theme, theme_from_preset, theme_options_text, theme_to_preset


class ThemeSupportMixin:
    """Shared theme API. Subclasses implement _apply_theme()."""

    _theme: str

    def _init_theme_support(self, theme: str = "material") -> None:
        self._theme = normalize_theme(theme)

    def getTheme(self) -> str:
        return self._theme

    def setTheme(self, value: str) -> None:
        theme = normalize_theme(value)
        changed = theme != self._theme
        self._theme = theme
        self._apply_theme()
        signal = getattr(self, "themeChanged", None)
        if changed and signal is not None:
            signal.emit(theme)

    def getThemeName(self) -> str:
        return self._theme

    def setThemeName(self, value: str) -> None:
        self.setTheme(value)

    def getThemeIndex(self) -> int:
        return theme_to_preset(self._theme)

    def setThemeIndex(self, value: int) -> None:
        self.setTheme(theme_from_preset(value))

    def getThemeOptions(self) -> str:
        return theme_options_text()

    def setThemeOptions(self, value: str) -> None:
        return None

