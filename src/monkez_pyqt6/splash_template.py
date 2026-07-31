from __future__ import annotations

import shutil
from pathlib import Path


DEFAULT_SPLASH_FILENAME = "splash_screen.ui"


def bundled_splash_template() -> Path:
    template = Path(__file__).resolve().parent / "templates" / "monkez_splash_screen.ui"
    if not template.is_file():
        raise FileNotFoundError(f"Bundled splash template was not found: {template}")
    return template


def create_splash_ui(destination: str | Path) -> tuple[Path, bool]:
    target = Path(destination).expanduser()
    if target.exists() and target.is_dir():
        target /= DEFAULT_SPLASH_FILENAME
    if target.suffix.lower() != ".ui":
        raise ValueError("Splash form destination must use the .ui extension.")

    target = target.resolve()
    if target.exists():
        if not target.is_file():
            raise ValueError(f"Splash form destination is not a file: {target}")
        return target, False

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(bundled_splash_template(), target)
    return target, True
