"""Small, typed helpers around :func:`PyQt6.uic.loadUi`."""

from __future__ import annotations

from os import PathLike
from pathlib import Path
from typing import Any, TypeVar, overload

from PyQt6 import uic
from PyQt6.QtWidgets import QWidget


UiPath = str | PathLike[str]
WidgetT = TypeVar("WidgetT", bound=QWidget)


class UiLoadError(RuntimeError):
    """Raised when a valid UI file cannot be constructed by PyQt6."""


def _ui_path(ui_file: UiPath) -> Path:
    path = Path(ui_file).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"Qt Designer UI file was not found: {path}")
    return path.resolve()


@overload
def load_ui(
    ui_file: UiPath,
    base_instance: WidgetT,
    *,
    parent: None = None,
    package: str = "",
) -> WidgetT: ...


@overload
def load_ui(
    ui_file: UiPath,
    base_instance: None = None,
    *,
    parent: QWidget | None = None,
    package: str = "",
) -> QWidget: ...


def load_ui(
    ui_file: UiPath,
    base_instance: WidgetT | None = None,
    *,
    parent: QWidget | None = None,
    package: str = "",
) -> WidgetT | QWidget:
    """Load a Designer ``.ui`` file as a new widget or into an existing one.

    ``load_ui("main.ui")`` creates and returns the top-level widget declared in
    the file. ``load_ui("main.ui", self)`` populates an existing ``QMainWindow``
    or ``QWidget`` and returns that same instance. For reusable child forms,
    ``parent=`` assigns a Qt parent to the newly created widget.
    """

    if base_instance is not None and parent is not None:
        raise ValueError("parent cannot be used together with base_instance")
    if base_instance is not None and not isinstance(base_instance, QWidget):
        raise TypeError("base_instance must be a QWidget")
    if parent is not None and not isinstance(parent, QWidget):
        raise TypeError("parent must be a QWidget")

    path = _ui_path(ui_file)

    # Ensure Monkez classes are registered before PyQt6 resolves custom-widget
    # headers. The module itself lazy-loads individual widgets.
    from . import monkez_widgets as _monkez_widgets  # noqa: F401

    try:
        widget = uic.loadUi(
            str(path),
            baseinstance=base_instance,
            package=package,
        )
    except Exception as exc:
        raise UiLoadError(f"Could not load Qt Designer UI file: {path}") from exc

    if not isinstance(widget, QWidget):
        raise UiLoadError(f"UI file did not create a QWidget: {path}")
    if parent is not None:
        widget.setParent(parent)
    return widget


def load_ui_into(
    base_instance: WidgetT,
    ui_file: UiPath,
    *,
    package: str = "",
) -> WidgetT:
    """Populate and return an existing ``QWidget`` or ``QMainWindow``."""

    return load_ui(
        ui_file,
        base_instance,
        package=package,
    )


class UiLoaderMixin:
    """Mixin adding ``self.load_ui(path)`` to QWidget subclasses."""

    def load_ui(
        self: WidgetT,
        ui_file: UiPath,
        *,
        package: str = "",
    ) -> WidgetT:
        return load_ui_into(
            self,
            ui_file,
            package=package,
        )
