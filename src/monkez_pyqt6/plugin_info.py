from __future__ import annotations

from .launcher import build_env, candidate_designer_paths, plugin_dir


def main() -> int:
    env = build_env()
    print(f"Plugin directory: {plugin_dir()}")
    print(f"QTDESIGNERPATH: {env.get('QTDESIGNERPATH', '')}")
    print(f"PYQTDESIGNERPATH: {env.get('PYQTDESIGNERPATH', '')}")
    print(f"PYTHONPATH: {env.get('PYTHONPATH', '')}")
    print(f"QT_PLUGIN_PATH: {env.get('QT_PLUGIN_PATH', '')}")
    print("Designer candidates:")
    for candidate in candidate_designer_paths():
        print(f"  - {candidate}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
