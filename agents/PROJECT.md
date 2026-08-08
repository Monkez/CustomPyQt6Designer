# Project context for AI agents

## Product boundaries

The repository ships two related products:

1. A Windows one-folder Qt Designer distribution with Python custom widget plugins.
2. A Python runtime package that applications install to load `.ui` files containing
   those custom widgets.

Do not make the runtime application depend on the portable Designer.

## Architecture

- `src/monkez_pyqt6/monkez_widgets`: runtime widget implementations.
- `src/monkez_pyqt6/monkez_widgets/monkez_canva.py`: runtime canvas/chart/flow
  editor; see `agents/MONKEZ_CANVA_ARCHITECTURE.md`.
- `src/monkez_pyqt6/designer_plugins`: Qt Designer plugin adapters.
- `src/monkez_pyqt6/launcher.py`: Designer discovery and environment setup.
- `src/monkez_pyqt6/gallery_app.py`: interactive widget documentation.
- `src/monkez_pyqt6/splash.py`: startup-optimized splash controller.
- `src/monkez_pyqt6/splash_template.py` and `templates/`: standalone
  splash form creation and the packaged Designer template.
- `src/monkez_pyqt6/startup_guard.py`: startup-only cross-process lock.
- `src/monkez_pyqt6/diagnostics.py`: actionable installation checks.
- `src/monkez_pyqt6/ui_loader.py`: canonical `.ui` loading helpers for new
  top-level forms, existing widgets and reusable child forms.
- `src/custom_pyqt6_designer`: compatibility namespace and legacy module
  launcher retained for projects created before 0.5.
- `demo_project`: end-to-end runtime example.
- `splash_heavy_demo`: standalone background-loading splash executable demo.
- `scripts/build_full_designer.ps1`: reproducible portable build and plugin verification.
- `scripts/build_splash_heavy_demo.ps1`: one-folder executable build and startup verification.
- `packaging/portable`: onboarding files copied into the portable release root.
- `tests`: offscreen widget, plugin, launcher, gallery, packaging and demo tests.

The canonical `.ui` header is:

```xml
<header>monkez_pyqt6.monkez_widgets</header>
```

The canonical distribution name is `monkez-pyqt6` and the canonical import
namespace is `monkez_pyqt6`. Keep the compatibility namespace lightweight and
do not use it in new examples or generated Designer headers.

Python 3.11 is required for the pinned `pyqt6-tools` Designer bridge.
Public widget classes are lazy-loaded from `monkez_widgets`; preserve this behavior
so importing the splash path does not load unrelated widgets or optional backends.
