"""Compatibility aliases for the unified :class:`MonkezButton` API.

New code should use ``MonkezButton`` with ``styleIndex`` and ``loading``.
These aliases remain importable for early adopters of the pre-release widgets,
but are intentionally hidden from the package export list and Qt Designer.
"""

from .monkez_button import MonkezButton


MonkezLoadingButton = MonkezButton
MonkezIconButton = MonkezButton

__all__ = ["MonkezLoadingButton", "MonkezIconButton"]
