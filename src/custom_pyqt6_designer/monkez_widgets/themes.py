from __future__ import annotations

from PyQt6.QtGui import QColor


THEME_NAMES = ("material", "ios", "fluent", "bootstrap", "minimal", "dark")
THEME_OPTIONS_TEXT = "0 Material | 1 iOS | 2 Fluent | 3 Bootstrap | 4 Minimal | 5 Dark"

THEMES = {
    "material": {
        "primary": "#1976d2",
        "primary_hover": "#1565c0",
        "primary_pressed": "#0d47a1",
        "on_primary": "#ffffff",
        "secondary": "#e3f2fd",
        "surface": "#ffffff",
        "surface_alt": "#f5faff",
        "control": "#ffffff",
        "control_hover": "#f1f8ff",
        "text": "#1f2937",
        "muted": "#607d8b",
        "border": "#90a4ae",
        "border_focus": "#1976d2",
        "danger": "#d32f2f",
        "success": "#2e7d32",
        "warning": "#ed6c02",
        "shadow": "#33000000",
        "radius": 8,
        "radius_lg": 12,
        "border_width": 1,
        "control_height": 40,
        "font_size": 14,
    },
    "ios": {
        "primary": "#007aff",
        "primary_hover": "#0a84ff",
        "primary_pressed": "#0060c7",
        "on_primary": "#ffffff",
        "secondary": "#e8f3ff",
        "surface": "#ffffff",
        "surface_alt": "#f2f2f7",
        "control": "#f9f9fb",
        "control_hover": "#ffffff",
        "text": "#1c1c1e",
        "muted": "#6e6e73",
        "border": "#d1d1d6",
        "border_focus": "#007aff",
        "danger": "#ff3b30",
        "success": "#34c759",
        "warning": "#ff9500",
        "shadow": "#24000000",
        "radius": 16,
        "radius_lg": 22,
        "border_width": 1,
        "control_height": 42,
        "font_size": 14,
    },
    "fluent": {
        "primary": "#0067c0",
        "primary_hover": "#005a9e",
        "primary_pressed": "#004578",
        "on_primary": "#ffffff",
        "secondary": "#eff6fc",
        "surface": "#ffffff",
        "surface_alt": "#f3f3f3",
        "control": "#ffffff",
        "control_hover": "#f9f9f9",
        "text": "#1b1b1b",
        "muted": "#606060",
        "border": "#c7c7c7",
        "border_focus": "#0067c0",
        "danger": "#c50f1f",
        "success": "#107c10",
        "warning": "#f7630c",
        "shadow": "#26000000",
        "radius": 4,
        "radius_lg": 8,
        "border_width": 1,
        "control_height": 36,
        "font_size": 13,
    },
    "bootstrap": {
        "primary": "#0d6efd",
        "primary_hover": "#0b5ed7",
        "primary_pressed": "#0a58ca",
        "on_primary": "#ffffff",
        "secondary": "#e7f1ff",
        "surface": "#ffffff",
        "surface_alt": "#f8f9fa",
        "control": "#ffffff",
        "control_hover": "#f8f9fa",
        "text": "#212529",
        "muted": "#6c757d",
        "border": "#ced4da",
        "border_focus": "#86b7fe",
        "danger": "#dc3545",
        "success": "#198754",
        "warning": "#ffc107",
        "shadow": "#260d6efd",
        "radius": 6,
        "radius_lg": 8,
        "border_width": 1,
        "control_height": 38,
        "font_size": 14,
    },
    "minimal": {
        "primary": "#111827",
        "primary_hover": "#374151",
        "primary_pressed": "#030712",
        "on_primary": "#ffffff",
        "secondary": "#f3f4f6",
        "surface": "#ffffff",
        "surface_alt": "#f9fafb",
        "control": "#ffffff",
        "control_hover": "#f9fafb",
        "text": "#111827",
        "muted": "#6b7280",
        "border": "#d1d5db",
        "border_focus": "#111827",
        "danger": "#b91c1c",
        "success": "#047857",
        "warning": "#b45309",
        "shadow": "#18000000",
        "radius": 6,
        "radius_lg": 6,
        "border_width": 1,
        "control_height": 36,
        "font_size": 13,
    },
    "dark": {
        "primary": "#38bdf8",
        "primary_hover": "#7dd3fc",
        "primary_pressed": "#0284c7",
        "on_primary": "#082f49",
        "secondary": "#172033",
        "surface": "#0f172a",
        "surface_alt": "#1e293b",
        "control": "#111827",
        "control_hover": "#1f2937",
        "text": "#f8fafc",
        "muted": "#94a3b8",
        "border": "#334155",
        "border_focus": "#38bdf8",
        "danger": "#fb7185",
        "success": "#4ade80",
        "warning": "#fbbf24",
        "shadow": "#66000000",
        "radius": 8,
        "radius_lg": 12,
        "border_width": 1,
        "control_height": 40,
        "font_size": 14,
    },
}


def normalize_theme(theme: str) -> str:
    value = (theme or "material").strip().lower()
    if value.isdigit():
        index = int(value)
        if 0 <= index < len(THEME_NAMES):
            return THEME_NAMES[index]
    return value if value in THEMES else "material"


def theme_from_preset(value) -> str:
    if isinstance(value, str):
        raw = value.strip()
        raw = raw.split("::")[-1].split(".")[-1]
        aliases = {
            "material": "material",
            "ios": "ios",
            "fluent": "fluent",
            "bootstrap": "bootstrap",
            "minimal": "minimal",
            "dark": "dark",
        }
        normalized = raw.replace("_", "").replace("-", "").lower()
        if normalized in aliases:
            return aliases[normalized]
        return normalize_theme(raw)

    try:
        index = int(value)
    except (TypeError, ValueError):
        return normalize_theme(str(value))
    if 0 <= index < len(THEME_NAMES):
        return THEME_NAMES[index]
    return "material"


def theme_to_preset(theme: str) -> int:
    value = normalize_theme(theme)
    return THEME_NAMES.index(value)


def theme_options_text() -> str:
    return THEME_OPTIONS_TEXT


def theme_value(theme: str, key: str):
    return THEMES[normalize_theme(theme)][key]


def theme_color(theme: str, key: str) -> QColor:
    return QColor(theme_value(theme, key))


def theme_int(theme: str, key: str) -> int:
    return int(theme_value(theme, key))


def theme_radius(theme: str) -> int:
    return int(theme_value(theme, "radius"))
