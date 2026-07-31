# Agent workflow

## Before changing code

1. Read `README.md`, the relevant file under `docs`, and `agents/STATUS.md`.
2. Inspect `git status` and preserve unrelated user changes.
3. Keep package versions synchronized between `pyproject.toml` and
   `src/monkez_pyqt6/__init__.py`.

## Validation

Run:

```powershell
lint.bat
test.bat
```

For release-affecting changes, also run:

```powershell
build.bat
```

The portable build is valid only after all 25 plugins initialize, create their
widgets and remain stable during verification.
The windowed Designer verifier must be started with
`Start-Process -Wait -PassThru`; a direct PowerShell invocation can return
before the GUI process releases its embedded Python archive.

For the standalone heavy splash demo, run `build_splash_demo.bat`. Its packaged
`--verify` run must exit successfully before the demo ZIP is accepted.
Because widgets are lazy-imported, the build must keep the explicit
`monkez_splash_screen` hidden import. GUI verification must use
`Start-Process -Wait -PassThru`; invoking a windowed executable directly does
not provide reliable completion or exit-code checking in this PowerShell flow.

For installation changes, verify:

1. `python -m monkez_pyqt6 --doctor` succeeds in `.venv311`.
2. `python -m custom_pyqt6_designer --version` still succeeds as the legacy
   compatibility launcher.
3. PowerShell installer/uninstaller scripts parse without syntax errors.
4. The portable build root contains `START_HERE.txt` and
   `Open Monkez Designer.bat` plus `New Splash Screen.bat`.
5. Never test the per-user installer against the developer's real
   `%LOCALAPPDATA%`; use static checks or an explicitly isolated test account.

The portable ZIP is created with `System.IO.Compression.ZipFile`. Keep
`includeBaseDirectory` disabled so the executable and onboarding files remain
at the archive root.

PyInstaller writes unpacked builds to `dist/portable/<version>/MonkezDesigner`.
This versioned location prevents an older running portable Designer from
locking and breaking a newer release build.
If that exact version is currently running, the build script automatically
uses `dist/portable/<version>-build-<timestamp>/MonkezDesigner` as an isolated
fallback while keeping the canonical release ZIP name.

The splash plugin is intentionally hidden from the Widget Box by returning
empty `domXml()`. Full Designer verification must open the packaged standalone
splash template so all 25 plugins are both initialized and constructed.

## Documentation

- User-facing behavior belongs in `README.md` or `docs`.
- Architecture, workflow and current engineering state belong in `agents`.
- Update documentation in the same change as implementation.

## Release

1. Confirm a clean test run.
2. Confirm version synchronization.
3. Build the wheel, source archive and portable ZIP.
4. Review the Git diff.
5. Commit with a focused message and push using `git`.
