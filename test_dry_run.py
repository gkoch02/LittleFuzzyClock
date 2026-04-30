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


if __name__ == "__main__":
    unittest.main()
