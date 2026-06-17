from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from PyQt6.QtGui import QColor


def to_color(value: QColor | str | Iterable[int]) -> QColor:
    if isinstance(value, QColor):
        return QColor(value)
    if isinstance(value, str):
        color = QColor(value)
        if not color.isValid():
            raise ValueError(f"Invalid color string: {value!r}")
        return color
    parts = list(value)
    if len(parts) not in {3, 4}:
        raise ValueError("Color tuples must have 3 or 4 integer components.")
    return QColor(*[int(part) for part in parts])


def _call_first(widget: Any, method_names: tuple[str, ...], *args) -> bool:
    for method_name in method_names:
        original = getattr(type(widget), f"__monkez_original_{method_name}", None)
        if callable(original):
            original(widget, *args)
            return True
        method = getattr(widget, method_name, None)
        raw_method = getattr(method, "__func__", method)
        if getattr(raw_method, "_monkez_fluent_api", False):
            continue
        if callable(method):
            method(*args)
            return True
    return False


def _require_supported(widget: Any, feature: str) -> None:
    raise AttributeError(f"{type(widget).__name__} does not expose a {feature} API.")


def set_background(self, color):
    color = to_color(color)
    if not _call_first(
        self,
        ("setBackgroundColor", "setActiveColor", "setBoxColor", "setTrackColor", "setGrooveColor"),
        color,
    ):
        _require_supported(self, "background color")
    return self


def set_foreground(self, color):
    color = to_color(color)
    if not _call_first(self, ("setTextColor", "setDigitColor", "setValueColor"), color):
        _require_supported(self, "foreground/text color")
    return self


def set_border(self, color):
    color = to_color(color)
    if not _call_first(self, ("setBorderColor",), color):
        _require_supported(self, "border color")
    return self


def set_accent(self, color):
    color = to_color(color)
    if not _call_first(
        self,
        ("setAccentColor", "setCheckedColor", "setFilledColor", "setValueColor", "setBarColor", "setActiveColor"),
        color,
    ):
        _require_supported(self, "accent color")
    return self


def set_track(self, color):
    color = to_color(color)
    if not _call_first(self, ("setTrackColor", "setGrooveColor", "setTrackColor"), color):
        _require_supported(self, "track color")
    return self


def set_thumb(self, color):
    color = to_color(color)
    if not _call_first(self, ("setThumbColor", "setHandleColor"), color):
        _require_supported(self, "thumb/handle color")
    return self


def set_content_padding(self, x: int, y: int | None = None):
    y = x if y is None else y
    if _call_first(self, ("setPaddingX",), int(x)):
        _call_first(self, ("setPaddingY",), int(y))
        return self
    if _call_first(self, ("setPadding", "setContentPadding"), int(x)):
        return self
    _require_supported(self, "padding")


def set_size_tokens(self, *, radius: int | None = None, border_width: int | None = None, control_height: int | None = None):
    if radius is not None:
        if not _call_first(self, ("setRadius",), int(radius)):
            _require_supported(self, "radius")
    if border_width is not None and not _call_first(self, ("setBorderWidth",), int(border_width)):
        _require_supported(self, "border width")
    if control_height is not None and not _call_first(
        self,
        ("setControlHeight", "setBarHeight", "setGrooveHeight"),
        int(control_height),
    ):
        _require_supported(self, "control height")
    return self


def set_shadow(self, enabled: bool = True, *, blur: int | None = None, offset_x: int | None = None,
               offset_y: int | None = None, color=None):
    if not _call_first(self, ("setShadowEnabled",), bool(enabled)):
        _require_supported(self, "shadow")
    if blur is not None:
        _call_first(self, ("setShadowBlur",), int(blur))
    if offset_x is not None:
        _call_first(self, ("setShadowOffsetX",), int(offset_x))
    if offset_y is not None:
        _call_first(self, ("setShadowOffsetY",), int(offset_y))
    if color is not None:
        _call_first(self, ("setShadowColor",), to_color(color))
    return self


def set_colors(self, **colors):
    mapping = {
        "background": set_background,
        "surface": set_background,
        "foreground": set_foreground,
        "text": set_foreground,
        "border": set_border,
        "accent": set_accent,
        "primary": set_accent,
        "track": set_track,
        "thumb": set_thumb,
        "handle": set_thumb,
    }
    for key, value in colors.items():
        setter = mapping.get(key)
        if setter is None:
            raise KeyError(f"Unknown color role: {key!r}")
        setter(self, value)
    return self


def install_fluent_api(classes: Iterable[type]) -> None:
    methods = {
        "setBackground": set_background,
        "setForeground": set_foreground,
        "setBorder": set_border,
        "setAccent": set_accent,
        "setTrack": set_track,
        "setThumb": set_thumb,
        "setContentPadding": set_content_padding,
        "setSizeTokens": set_size_tokens,
        "setShadow": set_shadow,
        "setColors": set_colors,
    }
    for method in methods.values():
        setattr(method, "_monkez_fluent_api", True)
    for cls in classes:
        for name, method in methods.items():
            original = getattr(cls, name, None)
            if original is not None and not getattr(original, "_monkez_fluent_api", False):
                setattr(cls, f"__monkez_original_{name}", original)
            setattr(cls, name, method)
