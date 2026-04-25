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


REPO_ROOT = os.path.dirname(os.path.abspath(__file__))


class DryRunCLITests(unittest.TestCase):
    def test_dry_run_writes_a_landscape_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_path = os.path.join(tmp, "preview.png")
            result = subprocess.run(
                [sys.executable, "fuzzyClock2.py", "--dry-run", "--output", out_path],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                result.returncode, 0,
                f"--dry-run exited {result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}",
            )
            self.assertTrue(os.path.exists(out_path), "PNG was not written")
            with Image.open(out_path) as img:
                self.assertEqual(img.size, (250, 122))
                self.assertEqual(img.mode, "1")


if __name__ == "__main__":
    unittest.main()
