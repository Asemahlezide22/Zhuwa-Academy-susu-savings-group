"""Tests for the plain-text group report."""

import unittest

from susu.group import SusuGroup
from susu.report import render_report


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.group = SusuGroup("50.00")
        for name in ("Ama", "Kofi", "Esi"):
            self.group.add_member(name)

    def test_report_mid_week_shows_paid_owing_and_history(self):
        # Finish week 1, then part-pay week 2.
        for name in self.group.members:
            self.group.contribute(name, 1, "50")
        self.group.close_week()
        self.group.contribute("Ama", 2, "50")
        self.group.contribute("Esi", 2, "30")

        report = render_report(self.group)
        self.assertIn("Current week: 2", report)
        self.assertIn("Next to receive the pot: Kofi", report)
        self.assertIn("Paid in full: Ama", report)
        self.assertIn("  Kofi: 50.00 (paid 0.00 so far)", report)
        self.assertIn("  Esi: 20.00 (paid 30.00 so far)", report)
        self.assertIn("  Week 1: Ama received GHS 150.00", report)

    def test_report_before_any_payment(self):
        report = render_report(self.group)
        self.assertIn("Current week: 1", report)
        self.assertIn("Paid in full: nobody yet", report)
        self.assertIn("  none yet", report)

    def test_report_after_full_cycle(self):
        for week in (1, 2, 3):
            for name in self.group.members:
                self.group.contribute(name, week, "50")
            self.group.close_week()
        report = render_report(self.group)
        self.assertIn("Cycle complete after week 3", report)
        self.assertIn("  Week 3: Esi received GHS 150.00", report)
        self.assertNotIn("Current week", report)


if __name__ == "__main__":
    unittest.main()
