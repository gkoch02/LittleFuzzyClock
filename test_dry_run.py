"""End-to-end test for fuzzyClock2.py --dry-run.

Exercises the CLI surface and the EPD-not-available fallback that the
dev script uses on non-Pi machines.

Run with: python3 -m unittest test_dry_run
"""

import os
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

from fuzzyclock_core import DIALECTS

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))


class DryRunCLITests(unittest.TestCase):
    """Existing end-to-end dry-run tests (basic image shape, dialects, bad dialect)."""

    def _run_dry(self, *extra_args):
        with tempfile.TemporaryDirectory() as tmp:
            out_path = os.path.join(tmp, "preview.png")
            result = subprocess.run(
                [
                    sys.executable,
                    "fuzzyClock2.py",
                    "--dry-run",
                    "--output",
                    out_path,
                    *extra_args,
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                result.returncode,
                0,
                f"--dry-run exited {result.returncode}\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}",
            )
            self.assertTrue(os.path.exists(out_path), "PNG was not written")
            with Image.open(out_path) as img:
                # Detach from the temp dir before it's cleaned up.
                img.load()
                return img

    def test_dry_run_writes_a_landscape_png(self):
        img = self._run_dry()
        self.assertEqual(img.size, (250, 122))
        self.assertEqual(img.mode, "1")

    def test_dry_run_supports_every_dialect(self):
        # Each dialect is rendered through the CLI surface end-to-end. Catches
        # any dialect that imports cleanly but blows up the dry-run path
        # specifically (font issues, layout overflow, etc.).
        for dialect in sorted(DIALECTS):
            with self.subTest(dialect=dialect):
                img = self._run_dry("--dialect", dialect)
                self.assertEqual(img.size, (250, 122))

    def test_unknown_dialect_is_rejected_by_argparse(self):
        # argparse `choices=` should refuse the value with a non-zero exit.
        result = subprocess.run(
            [sys.executable, "fuzzyClock2.py", "--dry-run", "--dialect", "esperanto"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid choice", result.stderr)


class DryRunTimeArgTests(unittest.TestCase):
    """Tests for the --time flag, which pins the clock face to a fixed HH:MM."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, *extra_args):
        """Return (CompletedProcess, out_path). out_path is valid while self.tmp is alive."""
        out_path = os.path.join(self.tmp.name, "preview.png")
        result = subprocess.run(
            [sys.executable, "fuzzyClock2.py", "--dry-run", "--output", out_path, *extra_args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        return result, out_path

    def test_valid_time_produces_correct_png(self):
        result, out_path = self._run("--time", "09:15")
        self.assertEqual(
            result.returncode,
            0,
            f"--time 09:15 exited {result.returncode}\nstderr: {result.stderr}",
        )
        with Image.open(out_path) as img:
            img.load()
            self.assertEqual(img.size, (250, 122))
            self.assertEqual(img.mode, "1")

    def test_boundary_midnight_renders(self):
        result, out_path = self._run("--time", "00:00")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertTrue(os.path.exists(out_path))

    def test_boundary_end_of_day_renders(self):
        result, out_path = self._run("--time", "23:59")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertTrue(os.path.exists(out_path))

    def test_invalid_hour_exits_nonzero(self):
        # datetime.strptime rejects "25:00"; the process should exit non-zero.
        result, _ = self._run("--time", "25:00")
        self.assertNotEqual(result.returncode, 0)

    def test_non_numeric_time_exits_nonzero(self):
        result, _ = self._run("--time", "abc")
        self.assertNotEqual(result.returncode, 0)

    def test_same_time_produces_identical_renders(self):
        # --time pins the clock to a deterministic moment; two runs at the
        # same time and default dialect must produce byte-identical PNG output.
        out1 = os.path.join(self.tmp.name, "r1.png")
        out2 = os.path.join(self.tmp.name, "r2.png")
        for out in (out1, out2):
            r = subprocess.run(
                [
                    sys.executable,
                    "fuzzyClock2.py",
                    "--dry-run",
                    "--output",
                    out,
                    "--time",
                    "14:30",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        with Image.open(out1) as i1, Image.open(out2) as i2:
            i1.load()
            i2.load()
            self.assertEqual(list(i1.getdata()), list(i2.getdata()))

    def test_different_times_produce_different_renders(self):
        # Verify --time is actually wired through: two distinct times (from
        # different 5-minute phrase buckets) must not produce the same image.
        out1 = os.path.join(self.tmp.name, "t1.png")
        out2 = os.path.join(self.tmp.name, "t2.png")
        for time_str, out in (("09:00", out1), ("09:30", out2)):
            r = subprocess.run(
                [
                    sys.executable,
                    "fuzzyClock2.py",
                    "--dry-run",
                    "--output",
                    out,
                    "--time",
                    time_str,
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        with Image.open(out1) as i1, Image.open(out2) as i2:
            i1.load()
            i2.load()
            self.assertNotEqual(list(i1.getdata()), list(i2.getdata()))


if __name__ == "__main__":
    unittest.main()
