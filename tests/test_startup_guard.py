from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from monkez_pyqt6.startup_guard import (
    StartupAlreadyRunningError,
    StartupInstanceGuard,
)


class StartupInstanceGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.lock_directory = Path(self.temporary_directory.name)
        self.guards: list[StartupInstanceGuard] = []

    def tearDown(self) -> None:
        for guard in reversed(self.guards):
            guard.release()
        self.temporary_directory.cleanup()

    def guard(self, application_id: str) -> StartupInstanceGuard:
        guard = StartupInstanceGuard(
            application_id,
            lock_directory=self.lock_directory,
        )
        self.guards.append(guard)
        return guard

    def test_concurrent_startup_is_blocked_then_allowed_after_release(self) -> None:
        first = self.guard("com.example.product")
        duplicate = self.guard("com.example.product")

        self.assertTrue(first.try_acquire())
        self.assertFalse(duplicate.try_acquire())

        first.release()
        self.assertTrue(duplicate.try_acquire())
        duplicate.release()

    def test_acquire_raises_a_clear_error_when_startup_is_busy(self) -> None:
        first = self.guard("com.example.product")
        duplicate = self.guard("com.example.product")
        first.acquire()

        with self.assertRaises(StartupAlreadyRunningError):
            duplicate.acquire()

    def test_different_application_ids_do_not_block_each_other(self) -> None:
        first = self.guard("com.example.product-a")
        second = self.guard("com.example.product-b")

        self.assertTrue(first.try_acquire())
        self.assertTrue(second.try_acquire())


if __name__ == "__main__":
    unittest.main()
