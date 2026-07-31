# Installation architecture

## Supported user journeys

### Portable Designer

The release ZIP is self-contained and requires no Python installation. The
root includes `START_HERE.txt`, `Open Monkez Designer.bat`,
`MonkezDesigner.exe` and `_internal`. Build scripts copy onboarding files from
`packaging/portable` after PyInstaller completes and before release validation.

### Per-user Designer installation

`install_designer.bat` requires Python 3.11 and installs into:

```text
%LOCALAPPDATA%\MonkezDesigner\venv
```

It installs the local source package with the `designer` extra, runs
`--doctor`, and delegates shortcut creation to
`scripts/install_user_designer.ps1`. It requires no elevation and does not
reuse a project virtual environment.

The installed Start Menu group contains Designer, Docs Lab and Uninstall.
Uninstall is guarded to remove only the exact per-user install root.

It also contains `New Monkez Splash Screen`, which runs `--new-splash` from the
user's Documents directory.

### Standalone splash form

The splash runtime plugin remains installed so Designer can render top-level
`MonkezSplashScreen` forms, but its empty `domXml()` hides it from the Widget
Box. `new_splash.bat`, the portable launcher and the installed shortcut all
create/open the packaged template as an independent `.ui` form.

### Project runtime

Applications install the base package only. They do not depend on Designer or
the per-user installation. Python 3.10+ remains supported for runtime usage.

## Diagnostics

`monkez_pyqt6.diagnostics` checks:

- runtime package and Python version;
- Python 3.11 compatibility for source-based Designer;
- exactly 25 shipped plugin modules;
- discoverable Qt Designer executable;
- available Python Designer bridge.

The same CLI is available through the console script and
`python -m monkez_pyqt6 --doctor`. Module invocation avoids common
Windows `PATH` issues after pip installation.
