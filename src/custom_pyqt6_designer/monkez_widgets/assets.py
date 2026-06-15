from __future__ import annotations

from pathlib import Path


ASSET_ROOT = Path(__file__).resolve().parent / "monkez_assets"


def icon_path(name: str) -> str:
    return str(ASSET_ROOT / "icons" / name)


def image_path(name: str) -> str:
    return str(ASSET_ROOT / "images" / name)
