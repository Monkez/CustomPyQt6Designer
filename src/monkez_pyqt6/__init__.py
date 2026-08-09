"""Monkez widgets, Designer integration and convenient PyQt6 UI loading."""

from __future__ import annotations

from importlib import import_module
from typing import Any


__version__ = "0.6.0"

_LAZY_UI_EXPORTS = {
    "UiLoadError",
    "UiLoaderMixin",
    "load_ui",
    "load_ui_into",
}

__all__ = [
    "__version__",
    "UiLoadError",
    "UiLoaderMixin",
    "load_ui",
    "load_ui_into",
]


def __getattr__(name: str) -> Any:
    if name in _LAZY_UI_EXPORTS:
        value = getattr(import_module(".ui_loader", __name__), name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
