from __future__ import annotations

import hashlib
import re
import tempfile
from pathlib import Path

from PyQt6.QtCore import QLockFile, QStandardPaths


class StartupAlreadyRunningError(RuntimeError):
    """Raised when another process currently owns the startup lock."""


class StartupInstanceGuard:
    """Cross-process lock held only while an application is starting.

    Unlike a traditional single-instance guard, callers explicitly release this
    lock as soon as initialization completes. More application instances can
    then be launched while previous instances remain open.
    """

    def __init__(
        self,
        application_id: str,
        *,
        lock_directory: str | Path | None = None,
        stale_lock_ms: int = 0,
    ) -> None:
        normalized_id = str(application_id).strip()
        if not normalized_id:
            raise ValueError("application_id must not be empty.")

        safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", normalized_id).strip("-._")
        safe_name = (safe_name or "application")[:48]
        digest = hashlib.sha256(normalized_id.encode("utf-8")).hexdigest()[:16]
        directory = (
            Path(lock_directory)
            if lock_directory is not None
            else self._default_lock_directory()
        )
        directory.mkdir(parents=True, exist_ok=True)

        self.application_id = normalized_id
        self.lock_path = directory / f"monkez-startup-{safe_name}-{digest}.lock"
        self._lock = QLockFile(str(self.lock_path))
        self._lock.setStaleLockTime(max(0, int(stale_lock_ms)))
        self._acquired = False

    @staticmethod
    def _default_lock_directory() -> Path:
        qt_temp = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.TempLocation
        )
        return Path(qt_temp) if qt_temp else Path(tempfile.gettempdir())

    @property
    def acquired(self) -> bool:
        return self._acquired

    def try_acquire(self, timeout_ms: int = 0) -> bool:
        """Try to own the startup slot, optionally waiting for a short timeout."""

        if self._acquired:
            return True
        self._acquired = bool(self._lock.tryLock(max(0, int(timeout_ms))))
        return self._acquired

    def acquire(self, timeout_ms: int = 0) -> "StartupInstanceGuard":
        """Acquire the startup slot or raise ``StartupAlreadyRunningError``."""

        if not self.try_acquire(timeout_ms):
            raise StartupAlreadyRunningError(
                f"Another {self.application_id!r} process is still starting."
            )
        return self

    def release(self) -> None:
        """Release the startup slot so another instance may start."""

        if not self._acquired:
            return
        self._lock.unlock()
        self._acquired = False

    def __enter__(self) -> "StartupInstanceGuard":
        return self.acquire()

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.release()
