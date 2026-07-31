"""Compatibility namespace for projects created before Monkez PyQt6 0.5."""

from __future__ import annotations

from importlib import import_module
import sys
from typing import Any


_canonical_package = import_module("monkez_pyqt6")
__version__ = _canonical_package.__version__
__all__ = list(_canonical_package.__all__)

# Let old submodule imports resolve from the canonical package directory. This
# keeps existing .ui headers and imports usable during the rename transition.
__path__ = [*__path__, *_canonical_package.__path__]
monkez_widgets = import_module("monkez_pyqt6.monkez_widgets")
sys.modules[f"{__name__}.monkez_widgets"] = monkez_widgets


def __getattr__(name: str) -> Any:
    return getattr(_canonical_package, name)
