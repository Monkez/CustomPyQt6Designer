# Project context for AI agents

## Product boundaries

The repository ships two related products:

1. A Windows one-folder Qt Designer distribution with Python custom widget plugins.
2. A Python runtime package that applications install to load `.ui` files containing
   those custom widgets.

Do not make the runtime application depend on the portable Designer.

## Architecture

- `src/custom_pyqt6_designer/monkez_widgets`: runtime widget implementations.
- `src/custom_pyqt6_designer/designer_plugins`: Qt Designer plugin adapters.
- `src/custom_pyqt6_designer/launcher.py`: Designer discovery and environment setup.
- `src/custom_pyqt6_designer/gallery_app.py`: interactive widget documentation.
- `src/custom_pyqt6_designer/splash.py`: startup-optimized splash controller.
- `src/custom_pyqt6_designer/startup_guard.py`: startup-only cross-process lock.
- `src/custom_pyqt6_designer/diagnostics.py`: actionable installation checks.
- `demo_project`: end-to-end runtime example.
- `splash_heavy_demo`: standalone background-loading splash executable demo.
- `scripts/build_full_designer.ps1`: reproducible portable build and plugin verification.
- `scripts/build_splash_heavy_demo.ps1`: one-folder executable build and startup verification.
- `packaging/portable`: onboarding files copied into the portable release root.
- `tests`: offscreen widget, plugin, launcher, gallery, packaging and demo tests.

The canonical `.ui` header is:

```xml
<header>custom_pyqt6_designer.monkez_widgets</header>
```

Python 3.11 is required for the pinned `pyqt6-tools` Designer bridge.
Public widget classes are lazy-loaded from `monkez_widgets`; preserve this behavior
so importing the splash path does not load unrelated widgets or optional backends.
