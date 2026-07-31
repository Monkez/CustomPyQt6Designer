from __future__ import annotations

import sys
import time

from monkez_pyqt6.startup_guard import StartupInstanceGuard


APPLICATION_ID = "com.monkez.splash-heavy-demo"
VERIFY_FLAG = "--verify"
VERIFY_LOCK_FLAG = "--verify-startup-lock"
DUPLICATE_STARTUP_EXIT_CODE = 73


def main() -> int:
    arguments = sys.argv[1:]
    guard = StartupInstanceGuard(APPLICATION_ID)
    if not guard.try_acquire():
        return (
            DUPLICATE_STARTUP_EXIT_CODE
            if VERIFY_LOCK_FLAG in arguments
            else 0
        )

    try:
        if VERIFY_LOCK_FLAG in arguments:
            time.sleep(1.5)
            return 0

        from splash_heavy_demo.app import run_app

        return run_app(
            guard,
            verification_mode=VERIFY_FLAG in arguments,
        )
    finally:
        guard.release()


if __name__ == "__main__":
    raise SystemExit(main())
