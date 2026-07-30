# Agent workflow

## Before changing code

1. Read `README.md`, the relevant file under `docs`, and `agents/STATUS.md`.
2. Inspect `git status` and preserve unrelated user changes.
3. Keep package versions synchronized between `pyproject.toml` and
   `src/custom_pyqt6_designer/__init__.py`.

## Validation

Run:

```powershell
test.bat
```

For release-affecting changes, also run:

```powershell
build.bat
```

The portable build is valid only after all 24 plugins initialize, create their
widgets and remain stable during verification.

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
