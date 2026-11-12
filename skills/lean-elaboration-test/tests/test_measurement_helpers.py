"""Exercise Lake timing units, scope selection, and committed size snapshots."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
SPEC = importlib.util.spec_from_file_location("parse_build_timings", SCRIPTS / "parse_build_timings.py")
timings = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(timings)


class BuildTimingTests(unittest.TestCase):
    def test_seconds_milliseconds_ansi_and_missing_timings(self):
        log = (
            "✔ [1/4] Built Project.A (2.5s)\n"
            "\x1b[32m✔ [2/4] Built Project.B (125ms)\x1b[0m\n"
            "✔ [3/4] Built Project.C (0ms)\n"
            "✔ [4/4] Built Project.D\n"
        )
        report = timings.parse_timings(log, ("Project",))
        self.assertEqual(report["build_actions"], 4)
        self.assertEqual(report["timed_build_actions"], 3)
        self.assertEqual(report["untimed_build_actions"], 1)
        self.assertAlmostEqual(report["sum_elapsed_seconds"], 2.625)
        self.assertIsNone(report["actions"][-1]["elapsed_seconds"])

    def test_root_boundaries_facets_and_repeated_actions(self):
        log = (
            "✔ [1/7] Built Project (1s)\n"
            "✔ [2/7] Built Project.A:olean (2s)\n"
            "✔ [3/7] Built Project.A:olean (3s)\n"
            "✔ [4/7] Built Project:static (4s)\n"
            "✔ [5/7] Built ProjectExtra.A (5s)\n"
            "✔ [6/7] Built Mathlib.A (6s)\n"
            "✔ [7/7] Built Other.A (7s)\n"
        )
        report = timings.parse_timings(log, ("Project", "Other"))
        self.assertEqual(report["build_actions"], 5)
        self.assertEqual(report["sum_elapsed_seconds"], 17)
        self.assertEqual(report["actions"][1]["target"], report["actions"][2]["target"])

    def test_replays_failures_and_other_units_are_not_build_timings(self):
        report = timings.parse_timings(
            "✔ [1/3] Replayed Project.A (1s)\n"
            "✖ [2/3] Building Project.B (2s)\n"
            "✔ [3/3] Built Project.C (3m)\n"
        )
        self.assertEqual(report["build_actions"], 0)

    def test_diagnostic_text_is_not_a_build_action(self):
        report = timings.parse_timings(
            "info: example says Built Project.A (100s)\n"
            "Built Project.B (200s)\n"
            "quoted: ✔ [1/1] Built Project.C (300s)\n"
            "[1/1] Built Project.D (400ms)\n"
        )
        self.assertEqual(report["build_actions"], 1)
        self.assertEqual(report["sum_elapsed_seconds"], 0.4)

    def test_optional_build_actions_and_native_facets_remain_visible(self):
        report = timings.parse_timings(
            "✔ [1/2] (Optional) Built Project.A:c.o (2s)\n"
            "⚠ [2/2] Built Project.A (3s)\n",
            ("Project",),
        )
        self.assertEqual(report["build_actions"], 2)
        self.assertEqual(report["sum_elapsed_seconds"], 5)
        self.assertEqual(report["actions"][0]["target"], "Project.A:c.o")

    def test_cli_reports_json_and_rejects_empty_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "build.log"
            log.write_text("✔ [1/1] Built Project.A (250ms)\n")
            command = [sys.executable, str(SCRIPTS / "parse_build_timings.py"), str(log)]
            result = subprocess.run(command + ["--root-module", "Project"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["sum_elapsed_seconds"], 0.25)
            result = subprocess.run(command + ["--root-module", "Absent"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("no matching Built actions", result.stderr)


class SizeSnapshotTests(unittest.TestCase):
    def test_committed_legacy_and_module_files_with_comment_only_exclusion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def git(*args):
                return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)

            git("init", "-q")
            for name, content in {
                "Legacy.lean": "def legacy : Nat := 1\n",
                "Modular.lean": "/- outer /- nested -/ comment -/\nmodule\npublic def x : Nat := 1\n",
                "Comments.lean": "-- notes\n/- more notes -/\n",
                "lakefile.lean": "import Lake\n",
            }.items():
                (root / name).write_text(content)
            git("add", ".")
            git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                "commit", "-qm", "snapshot")
            # A dirty working tree must not change the committed size snapshot.
            (root / "Legacy.lean").write_text("module\npublic def legacy : Nat := 1\n")
            (root / "Untracked.lean").write_text("def untracked := 1\n")
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "count_lean_lines.py"), "HEAD"],
                cwd=root, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("counted files:                  3", result.stdout)
            self.assertIn("total lines (counted files):    5", result.stdout)
            self.assertIn("non-module files:               1", result.stdout)
            listed = result.stdout.split("non-module files (informational):", 1)[1]
            self.assertEqual(listed.strip(), "Legacy.lean")
            self.assertNotIn("Untracked.lean", result.stdout)


if __name__ == "__main__":
    unittest.main()
