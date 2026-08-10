# Monkez PyQt6 0.6.2

- Project scaffolds now use `uv` to provision a managed Python runtime and
  project-local `.venv` without installing a Python version system-wide.
- `setup.bat` bootstraps uv when needed and reinstalls all dependencies from
  `requirements.txt` after a project is copied to another computer.
