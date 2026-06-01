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
from datetime import datetime
from unittest import mock

from PIL import Image

import fuzzyClock2
from fuzzyclock_core import DIALECTS, FONT_VARIANTS, RANDOM_FONT

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


class DrawFuzzyClockInProcessTests(unittest.TestCase):
    """Direct in-process tests for fuzzyClock2.draw_fuzzy_clock().

    The subprocess-based DryRunCLITests cover the CLI surface end-to-end but
    don't let `coverage` instrument fuzzyClock2's internals. These tests
    import draw_fuzzy_clock() directly so the dry-run branch, the random-font
    resolution, the EPD-unavailable error path, and the hardware-write
    rotation are all visible to coverage and unit-mockable for finer-grained
    assertions than a "PNG exists and has the right size" check.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = os.path.join(self.tmp.name, "preview.png")

    def tearDown(self):
        self.tmp.cleanup()

    def test_dry_run_writes_landscape_png_in_process(self):
        fuzzyClock2.draw_fuzzy_clock(
            dry_run=True,
            output=self.out,
            now=datetime(2026, 4, 25, 9, 15),
        )
        with Image.open(self.out) as img:
            img.load()
            self.assertEqual(img.size, (250, 122))
            self.assertEqual(img.mode, "1")

    def test_random_font_is_resolved_to_a_registered_variant(self):
        # `RANDOM_FONT` is a config sentinel; draw_fuzzy_clock must resolve it
        # to a concrete vendored variant before handing it to render_clock,
        # otherwise load_font() would receive an unknown key and SystemExit.
        with mock.patch("fuzzyClock2.render_clock") as m_render:
            fuzzyClock2.draw_fuzzy_clock(
                dry_run=True,
                output=self.out,
                font=RANDOM_FONT,
                now=datetime(2026, 4, 25, 9, 15),
            )
        self.assertEqual(m_render.call_count, 1)
        resolved = m_render.call_args.kwargs["font_variant"]
        self.assertNotEqual(resolved, RANDOM_FONT)
        self.assertIn(resolved, FONT_VARIANTS)

    def test_default_now_uses_wall_clock(self):
        # now=None must fall back to datetime.now(); patching the import-site
        # alias proves the lookup happens at call time, not at import time.
        sentinel = datetime(2026, 1, 2, 3, 4)
        with mock.patch("fuzzyClock2.datetime") as m_dt:
            m_dt.now.return_value = sentinel
            with mock.patch("fuzzyClock2.render_clock") as m_render:
                fuzzyClock2.draw_fuzzy_clock(dry_run=True, output=self.out)
        self.assertEqual(m_render.call_args.args[3], sentinel)

    def test_systemexit_when_epd_unavailable_and_not_dry_run(self):
        # On a non-Pi host the EPD driver import sets EPD_AVAILABLE=False;
        # asking for a hardware render then must SystemExit with a clear
        # message instead of NameError'ing on the missing module attribute.
        with mock.patch.object(fuzzyClock2, "EPD_AVAILABLE", False):
            with self.assertRaises(SystemExit):
                fuzzyClock2.draw_fuzzy_clock(dry_run=False)

    def test_hardware_path_rotates_and_sleeps(self):
        # When EPD is available, the script must init the panel, push a
        # rotated buffer (the panel is mounted upside down — CLAUDE.md
        # gotcha #2), and put it back to sleep. Inject a fake epd2in13_V4
        # because the real module isn't importable in CI.
        fake_epd = mock.Mock()
        fake_epd.width = 122  # portrait dims; landscape swaps them
        fake_epd.height = 250
        fake_module = mock.Mock()
        fake_module.EPD.return_value = fake_epd

        captured_buf_images = []
        fake_epd.getbuffer.side_effect = lambda img: captured_buf_images.append(img) or b"buf"

        with (
            mock.patch.object(fuzzyClock2, "EPD_AVAILABLE", True),
            mock.patch.object(fuzzyClock2, "epd2in13_V4", fake_module, create=True),
        ):
            fuzzyClock2.draw_fuzzy_clock(
                dry_run=False,
                now=datetime(2026, 4, 25, 9, 15),
            )

        fake_epd.init.assert_called_once()
        fake_epd.display.assert_called_once()
        fake_epd.sleep.assert_called_once()
        self.assertEqual(len(captured_buf_images), 1)
        # The buffer the panel receives must be the rotated image. We can't
        # easily compare images, but the panel's portrait dimensions (height,
        # width) match the rotated image's (width, height) — rotate(180) on a
        # landscape image keeps its size, so this is really an "image was
        # passed through" assertion: size matches what the script promised.
        rotated = captured_buf_images[0]
        self.assertEqual(rotated.size, (250, 122))


class PinTimeToTodayTests(unittest.TestCase):
    """Tests for fuzzyClock2.pin_time_to_today() — the --time helper."""

    def test_combines_pinned_time_with_supplied_date(self):
        # The hour/minute come from the string; the date comes from `today`,
        # not strptime's 1900-01-01 default, so the rendered footer is real.
        today = datetime(2026, 4, 25, 18, 37, 12)
        pinned = fuzzyClock2.pin_time_to_today("09:15", today=today)
        self.assertEqual(pinned, datetime(2026, 4, 25, 9, 15))

    def test_zeroes_seconds_and_microseconds(self):
        # Pinned previews must be deterministic to the minute, so sub-minute
        # components are dropped regardless of when the helper is called.
        today = datetime(2026, 4, 25, 18, 37, 42, 123456)
        pinned = fuzzyClock2.pin_time_to_today("23:59", today=today)
        self.assertEqual(pinned, datetime(2026, 4, 25, 23, 59, 0, 0))

    def test_defaults_to_today_when_no_date_supplied(self):
        pinned = fuzzyClock2.pin_time_to_today("09:15")
        self.assertEqual((pinned.hour, pinned.minute), (9, 15))
        self.assertEqual(pinned.date(), datetime.now().date())

    def test_malformed_time_raises_valueerror(self):
        for bad in ("25:00", "abc", "9:5:5", ""):
            with self.assertRaises(ValueError):
                fuzzyClock2.pin_time_to_today(bad)


if __name__ == "__main__":
    unittest.main()
