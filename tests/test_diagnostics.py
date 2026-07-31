from __future__ import annotations

import io
import unittest
from unittest.mock import patch

import monkez_pyqt6.diagnostics as diagnostics
from monkez_pyqt6.diagnostics import DiagnosticCheck


class DiagnosticsTests(unittest.TestCase):
    def test_doctor_returns_success_when_all_checks_pass(self) -> None:
        stream = io.StringIO()
        checks = [
            DiagnosticCheck("Runtime package", True, "installed"),
            DiagnosticCheck("Qt Designer", True, "designer.exe"),
        ]

        with patch.object(diagnostics, "collect_diagnostics", return_value=checks):
            result = diagnostics.run_doctor(stream)

        self.assertEqual(result, 0)
        self.assertIn("ready to open Monkez Designer", stream.getvalue())

    def test_doctor_reports_actionable_failures(self) -> None:
        stream = io.StringIO()
        checks = [
            DiagnosticCheck(
                "Qt Designer",
                False,
                "Not found",
                'Install with the "designer" extra.',
            )
        ]

        with patch.object(diagnostics, "collect_diagnostics", return_value=checks):
            result = diagnostics.run_doctor(stream)

        self.assertEqual(result, 2)
        self.assertIn("[ERROR] Qt Designer", stream.getvalue())
        self.assertIn("Fix:", stream.getvalue())


if __name__ == "__main__":
    unittest.main()
