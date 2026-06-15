from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path


ENV_DESIGNER_EXE = "CUSTOM_PYQT6_DESIGNER_EXE"
VENV_NAMES = (".venv311", ".venv", ".venv312", "venv")


def package_root() -> Path:
    return Path(__file__).resolve().parent


def plugin_dir() -> Path:
    return package_root() / "designer_plugins"


def candidate_roots() -> list[Path]:
    roots: list[Path] = [Path.cwd()]
    if getattr(sys, "frozen", False):
        roots.append(Path(sys.executable).resolve().parent)
    roots.extend(package_root().parents)

    expanded: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        try:
            resolved = root.resolve()
        except OSError:
            resolved = root
        for candidate in (resolved, *resolved.parents[:4]):
            if candidate not in seen:
                expanded.append(candidate)
                seen.add(candidate)
    return expanded


def candidate_venv_scripts_dirs() -> list[Path]:
    scripts_dirs = [Path(sys.executable).resolve().parent]
    for root in candidate_roots():
        for venv_name in VENV_NAMES:
            scripts_dirs.append(root / venv_name / "Scripts")

    seen: set[Path] = set()
    unique: list[Path] = []
    for scripts_dir in scripts_dirs:
        if scripts_dir not in seen:
            unique.append(scripts_dir)
            seen.add(scripts_dir)
    return unique


def candidate_site_packages_dirs() -> list[Path]:
    candidates = []
    if getattr(sys, "frozen", False):
        internal_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        exe_internal_dir = Path(sys.executable).resolve().parent / "_internal"
        for bundled_dir in (internal_dir, exe_internal_dir):
            if (bundled_dir / "PyQt6").is_dir() and (bundled_dir / "qt6_applications").is_dir():
                return [bundled_dir]
        candidates.extend([internal_dir, exe_internal_dir])
    candidates.extend(
        [
            Path(sys.prefix) / "Lib" / "site-packages",
            Path(sys.base_prefix) / "Lib" / "site-packages",
        ]
    )
    for scripts_dir in candidate_venv_scripts_dirs():
        candidates.append(scripts_dir.parent / "Lib" / "site-packages")

    seen: set[Path] = set()
    unique: list[Path] = []
    for candidate in candidates:
        if candidate.is_dir() and candidate not in seen:
            unique.append(candidate)
            seen.add(candidate)
    return unique


def candidate_designer_paths() -> list[Path]:
    candidates: list[Path] = []

    if configured := os.environ.get(ENV_DESIGNER_EXE):
        candidates.append(Path(configured))

    path_hit = shutil.which("designer") or shutil.which("designer.exe")
    if path_hit:
        candidates.append(Path(path_hit))

    scripts_dir = Path(sys.executable).resolve().parent
    candidates.extend(
        [
            scripts_dir / "designer.exe",
            scripts_dir / "designer",
            Path(sys.prefix) / "Lib" / "site-packages" / "qt6_applications" / "Qt" / "bin" / "designer.exe",
            Path(sys.prefix) / "Lib" / "site-packages" / "PyQt6" / "Qt6" / "bin" / "designer.exe",
        ]
    )
    for site_packages in candidate_site_packages_dirs():
        candidates.extend(
            [
                site_packages / "qt6_applications" / "Qt" / "bin" / "designer.exe",
                site_packages / "PyQt6" / "Qt6" / "bin" / "designer.exe",
            ]
        )

    seen: set[Path] = set()
    unique: list[Path] = []
    for candidate in candidates:
        resolved = candidate.expanduser()
        if resolved not in seen:
            unique.append(resolved)
            seen.add(resolved)
    return unique


def find_designer() -> Path | None:
    for candidate in candidate_designer_paths():
        if candidate.is_file():
            return candidate
    return None


def find_pyqt6_tools() -> str | None:
    path_hit = shutil.which("pyqt6-tools") or shutil.which("pyqt6-tools.exe")
    if path_hit:
        return path_hit

    scripts_dir = Path(sys.executable).resolve().parent
    candidates = []
    for scripts_dir in candidate_venv_scripts_dirs():
        candidates.extend([scripts_dir / "pyqt6-tools.exe", scripts_dir / "pyqt6-tools"])

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


def has_pyqt6_tools_bridge() -> bool:
    if find_pyqt6_tools() is None:
        return False
    if importlib.util.find_spec("pyqt6_plugins") is not None and importlib.util.find_spec("qt6_tools") is not None:
        return True
    return any(
        (site_packages / "pyqt6_plugins").is_dir() and (site_packages / "qt6_tools").is_dir()
        for site_packages in candidate_site_packages_dirs()
    )


def build_env(debug: bool = False) -> dict[str, str]:
    env = os.environ.copy()
    designer_plugins = str(plugin_dir())
    import_root = str(package_root().parent)
    path_separator = os.pathsep
    if getattr(sys, "frozen", False):
        internal_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        exe_internal_dir = Path(sys.executable).resolve().parent / "_internal"
        if any((path / "PyQt6").is_dir() and (path / "qt6_applications").is_dir() for path in (internal_dir, exe_internal_dir)):
            env["PYTHONPATH"] = ""

    env["PYQTDESIGNERPATH"] = append_path(env.get("PYQTDESIGNERPATH", ""), designer_plugins, path_separator)
    env["PYTHONPATH"] = append_path(env.get("PYTHONPATH", ""), import_root, path_separator)
    if getattr(sys, "frozen", False):
        internal_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        base_library = internal_dir / "base_library.zip"
        if base_library.is_file():
            env["PYTHONPATH"] = append_path(env.get("PYTHONPATH", ""), str(base_library), path_separator)
    add_pyqt_bridge_paths(env, path_separator)

    if debug:
        env["QT_DEBUG_PLUGINS"] = "1"

    return env


def add_pyqt_bridge_paths(env: dict[str, str], path_separator: str) -> None:
    pyqt_plugins_spec = importlib.util.find_spec("pyqt6_plugins")
    pyqt6_spec = importlib.util.find_spec("PyQt6")
    site_packages_dirs = candidate_site_packages_dirs()
    if pyqt_plugins_spec is not None and pyqt_plugins_spec.origin is not None:
        site_packages_dirs.insert(0, Path(pyqt_plugins_spec.origin).resolve().parent.parent)
    if pyqt6_spec is not None and pyqt6_spec.origin is not None:
        site_packages_dirs.insert(0, Path(pyqt6_spec.origin).resolve().parent.parent)

    for site_packages in reversed(site_packages_dirs):
        env["PYTHONPATH"] = append_path(env.get("PYTHONPATH", ""), str(site_packages), path_separator)

        pyqt_plugins_qt_plugins = site_packages / "pyqt6_plugins" / "Qt" / "plugins"
        pyqt_plugins_designer = pyqt_plugins_qt_plugins / "designer"
        if pyqt_plugins_designer.is_dir():
            env["QTDESIGNERPATH"] = append_path(
                env.get("QTDESIGNERPATH", ""),
                str(pyqt_plugins_designer),
                path_separator,
            )
        if pyqt_plugins_qt_plugins.is_dir():
            env["QT_PLUGIN_PATH"] = append_path(
                env.get("QT_PLUGIN_PATH", ""),
                str(pyqt_plugins_qt_plugins),
                path_separator,
            )

        pyqt_qt_root = site_packages / "PyQt6" / "Qt6"
        pyqt_qt_bin = pyqt_qt_root / "bin"
        pyqt_qt_plugins = pyqt_qt_root / "plugins"
        if pyqt_qt_bin.is_dir():
            env["PATH"] = append_path(env.get("PATH", ""), str(pyqt_qt_bin), path_separator)
        if pyqt_qt_plugins.is_dir():
            env["QT_PLUGIN_PATH"] = append_path(
                env.get("QT_PLUGIN_PATH", ""),
                str(pyqt_qt_plugins),
                path_separator,
            )

    for candidate in (Path(sys.base_prefix), Path(sys.prefix), Path(sys.executable).resolve().parent):
        if candidate.is_dir():
            env["PATH"] = append_path(env.get("PATH", ""), str(candidate), path_separator)
    if getattr(sys, "frozen", False):
        internal_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        if internal_dir.is_dir():
            env["PATH"] = append_path(env.get("PATH", ""), str(internal_dir), path_separator)


def append_path(existing: str, new_entry: str, separator: str) -> str:
    parts = [part for part in existing.split(separator) if part]
    if new_entry not in parts:
        parts.insert(0, new_entry)
    return separator.join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Launch Qt Designer with Custom PyQt6 Designer plugins.")
    parser.add_argument("ui_file", nargs="?", help="Optional .ui file to open.")
    parser.add_argument("--designer", help=f"Path to designer executable. Overrides {ENV_DESIGNER_EXE}.")
    parser.add_argument("--debug", action="store_true", help="Enable Qt plugin debug output.")
    parser.add_argument("--print-env", action="store_true", help="Print environment values without launching.")
    args = parser.parse_args(argv)

    if args.designer:
        os.environ[ENV_DESIGNER_EXE] = args.designer

    env = build_env(debug=args.debug)

    if args.print_env:
        print(f"PYQTDESIGNERPATH={env.get('PYQTDESIGNERPATH', '')}")
        print(f"PYTHONPATH={env.get('PYTHONPATH', '')}")
        print(f"{ENV_DESIGNER_EXE}={os.environ.get(ENV_DESIGNER_EXE, '')}")
        return 0

    if has_pyqt6_tools_bridge():
        command = [find_pyqt6_tools() or "pyqt6-tools", "designer", "-p", str(plugin_dir())]
        if args.debug:
            command.append("--qt-debug-plugins")
        if args.ui_file:
            command.append(args.ui_file)
        return subprocess.call(command, env=env)

    designer = find_designer()
    command: list[str]
    if designer is not None:
        command = [str(designer)]
    else:
        pyqt6_tools = shutil.which("pyqt6-tools")
        if pyqt6_tools:
            command = [pyqt6_tools, "designer"]
        else:
            print(
                "Khong tim thay Qt Designer. Cai Qt/Qt Creator hoac pyqt6-tools, "
                f"hoac set {ENV_DESIGNER_EXE}=duong_dan_toi_designer.exe",
                file=sys.stderr,
            )
            print("Da thu cac duong dan:", file=sys.stderr)
            for candidate in candidate_designer_paths():
                print(f"  - {candidate}", file=sys.stderr)
            return 2

    if args.ui_file:
        command.append(args.ui_file)

    return subprocess.call(command, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
