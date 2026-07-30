from __future__ import annotations

import unittest

from splash_heavy_demo.app import HeavyStartupWorker, resource_path


class HeavySplashDemoTests(unittest.TestCase):
    def test_worker_reports_monotonic_progress_and_results(self) -> None:
        worker = HeavyStartupWorker(0.001)
        updates: list[tuple[int, str]] = []
        results: list[dict] = []
        failures: list[str] = []
        worker.progress.connect(lambda value, status: updates.append((value, status)))
        worker.ready.connect(results.append)
        worker.failed.connect(failures.append)

        worker.run()

        self.assertFalse(failures)
        self.assertEqual(updates[-1][0], 100)
        self.assertEqual(
            [value for value, _ in updates],
            sorted(value for value, _ in updates),
        )
        self.assertEqual(len(results), 1)
        self.assertGreaterEqual(results[0]["asset_megabytes"], 1)

    def test_source_asset_can_be_resolved(self) -> None:
        self.assertTrue(resource_path("logo.png").is_file())


if __name__ == "__main__":
    unittest.main()
