"""End-to-end tests: run CLI commands against a temporary group file."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from susu.cli import main


class CliTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.state = Path(self._tmp.name) / "group.json"

    def tearDown(self):
        self._tmp.cleanup()

    def run_cli(self, *args):
        """Run one command; return (exit code, stdout, stderr)."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["--state", str(self.state), *args])
        return code, out.getvalue(), err.getvalue()

    def test_example_from_the_brief_across_separate_runs(self):
        self.assertEqual(self.run_cli("create", "50.00")[0], 0)
        self.assertEqual(self.run_cli("add", "Ama", "Kofi", "Esi")[0], 0)
        self.run_cli("pay", "Ama", "50", "--week", "1")
        self.run_cli("pay", "Kofi", "50", "--week", "1")
        code, out, _ = self.run_cli("pay", "Esi", "30", "--week", "1")
        self.assertIn("Esi still owes 20.00 for week 1", out)

        code, out, _ = self.run_cli("close")
        self.assertEqual(code, 0)
        self.assertIn("Week 1 cannot close: Esi owes 20.00.", out)

        self.run_cli("pay", "esi", "20")  # week defaults to the open week
        code, out, _ = self.run_cli("close")
        self.assertIn("Week 1 closed: Ama receives 150.00. Week 2 begins; Kofi is next.", out)

        code, out, _ = self.run_cli("report")
        self.assertIn("Current week: 2", out)
        self.assertIn("Week 1: Ama received GHS 150.00", out)

    def test_refused_action_exits_1_and_leaves_file_unchanged(self):
        self.run_cli("create", "50")
        self.run_cli("add", "Ama", "Kofi")
        before = self.state.read_text(encoding="utf-8")
        for args in (("pay", "Yaw", "10"), ("pay", "Ama", "60"), ("pay", "Ama", "0"), ("add", "Esi", "ama")):
            with self.subTest(args=args):
                code, _, err = self.run_cli(*args)
                self.assertEqual(code, 1)
                self.assertTrue(err.startswith("Error: "))
                self.assertEqual(self.state.read_text(encoding="utf-8"), before)

    def test_create_refuses_to_overwrite_without_force(self):
        self.run_cli("create", "50")
        self.assertEqual(self.run_cli("create", "20")[0], 1)
        self.assertEqual(self.run_cli("create", "20", "--force")[0], 0)

    def test_commands_need_a_group_first(self):
        code, _, err = self.run_cli("report")
        self.assertEqual(code, 1)
        self.assertIn("Create one first", err)

    def test_tampered_file_is_refused(self):
        self.run_cli("create", "50")
        self.run_cli("add", "Ama", "Kofi")
        self.run_cli("pay", "Ama", "50")
        # Hand-edit the file to close week 1 although Kofi has not paid.
        state = json.loads(self.state.read_text(encoding="utf-8"))
        state["events"].append({"action": "close_week"})
        self.state.write_text(json.dumps(state), encoding="utf-8")
        code, _, err = self.run_cli("report")
        self.assertEqual(code, 1)
        self.assertIn("not fully paid", err)

    def test_amounts_are_saved_as_exact_strings(self):
        self.run_cli("create", "50")
        self.run_cli("add", "Ama", "Kofi")
        self.run_cli("pay", "ama", "12.5")
        event = json.loads(self.state.read_text(encoding="utf-8"))["events"][-1]
        self.assertEqual(event, {"action": "contribute", "member": "Ama", "week": 1, "amount": "12.50"})

    def test_demo_runs_the_brief_example(self):
        code, out, _ = self.run_cli("demo")
        self.assertEqual(code, 0)
        self.assertIn("Week 1 cannot close: Esi owes 20.00.", out)
        self.assertIn("Ama receives 150.00", out)
        self.assertFalse(self.state.exists())  # demo saves nothing


if __name__ == "__main__":
    unittest.main()
