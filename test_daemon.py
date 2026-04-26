"""Unit tests for the pure helpers in fuzzyclock_daemon.

Covers `current_mode` (across the day/night/after-hours branch table),
`_sleep_to_next_tick` (boundary math), `_load_coordinates` (config-file
error paths), and `_resolve_dialect` (environment-variable handling).

The daemon's hardware imports are guarded (see fuzzyclock_daemon top-of-file),
so this test file imports the module directly without stubbing GPIO/EPD.
"""

import json
import os
import tempfile
import unittest
from datetime import UTC, datetime
from unittest import mock

import fuzzyclock_daemon as d


class CurrentModeTests(unittest.TestCase):
    """Pure-function tests after the B1 signature refactor."""

    def setUp(self):
        # The daemon caches sun_times by (date, lat, lon). Clear it between
        # tests so a future patched _raw_sun_times can't be shadowed by an
        # entry left over from a real-math test.
        d._sun_times_cached.cache_clear()

    def _at(self, hour, minute=0, month=4, day=26):
        # 2026-04-26 is the project's notional "today"; specific date only
        # matters when after_hours_enabled is True (sun_times runs).
        return datetime(2026, month, day, hour, minute, tzinfo=UTC)

    def test_before_wake_window_is_night(self):
        self.assertEqual(d.current_mode(self._at(5), None, None, False), "night")
        # Even with coordinates configured, before DAY_START_HOUR is night.
        self.assertEqual(d.current_mode(self._at(6, 59), 51.5, -0.1, True), "night")

    def test_after_wake_window_is_night(self):
        # DAY_END_HOUR is exclusive: hour 23 is night.
        self.assertEqual(d.current_mode(self._at(23), None, None, False), "night")
        self.assertEqual(d.current_mode(self._at(23, 30), 51.5, -0.1, True), "night")

    def test_wake_window_without_coordinates_is_always_day(self):
        for hour in (7, 12, 18, 22):
            with self.subTest(hour=hour):
                self.assertEqual(
                    d.current_mode(self._at(hour), None, None, False),
                    "day",
                )

    def test_after_hours_during_summer_evening_in_london(self):
        # London at June solstice: sunset ~20:21 UTC. 21:00 is past sunset
        # but still inside the 7..23 wake window → after_hours.
        when = datetime(2024, 6, 21, 21, 0, tzinfo=UTC)
        self.assertEqual(d.current_mode(when, 51.5074, -0.1278, True), "after_hours")

    def test_day_during_summer_afternoon_in_london(self):
        # 14:00 UTC, sun is well up → day.
        when = datetime(2024, 6, 21, 14, 0, tzinfo=UTC)
        self.assertEqual(d.current_mode(when, 51.5074, -0.1278, True), "day")

    def test_polar_midnight_sun_falls_back_to_day(self):
        # Tromsø in summer: sun never sets → sun_times returns (None, None)
        # and the function falls back to "day" inside the wake window.
        when = datetime(2024, 6, 21, 12, 0, tzinfo=UTC)
        self.assertEqual(d.current_mode(when, 69.6492, 18.9553, True), "day")

    def test_custom_wake_window_overrides_module_defaults(self):
        # A caller can override day_start/day_end without touching globals.
        when = self._at(6)
        self.assertEqual(
            d.current_mode(when, None, None, False, day_start=5, day_end=22),
            "day",
        )

    def test_exact_sunset_boundary_is_still_day(self):
        # Comparison is inclusive on both ends (sunrise <= now <= sunset).
        # Mock _sun_times_cached so this test doesn't depend on the real
        # ephemeris numbers — we just want to verify the boundary semantics.
        sunrise = datetime(2024, 6, 21, 5, 0, tzinfo=UTC)
        sunset = datetime(2024, 6, 21, 20, 0, tzinfo=UTC)
        with mock.patch.object(d, "_sun_times_cached", return_value=(sunrise, sunset)):
            self.assertEqual(d.current_mode(sunset, 0.0, 0.0, True), "day")
            one_second_later = sunset.replace(second=1)
            self.assertEqual(d.current_mode(one_second_later, 0.0, 0.0, True), "after_hours")


class RenderStateTests(unittest.TestCase):
    """The cross-thread retry counter and recovery flag added during the
    code-review fixes; lets the button thread's failures trigger main-loop
    recovery, and lets goodnight clear stale failure state."""

    def setUp(self):
        # Reset module state between tests so they don't bleed.
        d._on_render_success()

    def tearDown(self):
        d._on_render_success()

    def test_success_clears_counter_and_recovery_flag(self):
        for _ in range(d.RENDER_RETRY_REINIT):
            d._on_render_failure()
        self.assertTrue(d._needs_recovery)
        d._on_render_success()
        self.assertEqual(d._consecutive_failures, 0)
        self.assertFalse(d._needs_recovery)

    def test_recovery_flag_flips_at_reinit_threshold(self):
        for _ in range(d.RENDER_RETRY_REINIT - 1):
            count, fatal = d._on_render_failure()
            self.assertFalse(fatal)
            self.assertFalse(d._needs_recovery)
        count, fatal = d._on_render_failure()
        self.assertEqual(count, d.RENDER_RETRY_REINIT)
        self.assertTrue(d._needs_recovery)
        self.assertFalse(fatal)

    def test_fatal_returned_at_fatal_threshold(self):
        fatal = False
        for _ in range(d.RENDER_RETRY_FATAL):
            _count, fatal = d._on_render_failure()
        self.assertTrue(fatal)


class SleepToNextTickTests(unittest.TestCase):
    """The result is always in (0, interval]; never zero (which would busy-loop)."""

    def test_exact_boundary_returns_full_interval(self):
        self.assertEqual(d._sleep_to_next_tick(60, now=0.0), 60.0)
        self.assertEqual(d._sleep_to_next_tick(60, now=60.0), 60.0)
        self.assertEqual(d._sleep_to_next_tick(300, now=900.0), 300.0)

    def test_mid_bucket_returns_remainder(self):
        self.assertEqual(d._sleep_to_next_tick(60, now=90.0), 30.0)
        self.assertEqual(d._sleep_to_next_tick(300, now=12.5), 287.5)

    def test_just_before_next_boundary(self):
        self.assertAlmostEqual(d._sleep_to_next_tick(60, now=119.5), 0.5)

    def test_default_now_uses_wall_clock(self):
        # Mocking time.time keeps this deterministic.
        with mock.patch("fuzzyclock_daemon.time.time", return_value=42.0):
            self.assertEqual(d._sleep_to_next_tick(60), 18.0)


class LoadCoordinatesTests(unittest.TestCase):
    def _write(self, contents):
        path = os.path.join(self.tmp.name, "fuzzyclock_config.json")
        with open(path, "w") as f:
            f.write(contents)
        return path

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_file_disables_after_hours(self):
        missing = os.path.join(self.tmp.name, "does_not_exist.json")
        self.assertEqual(d._load_coordinates(missing), (None, None))

    def test_malformed_json_disables_after_hours(self):
        path = self._write("{not valid json")
        self.assertEqual(d._load_coordinates(path), (None, None))

    def test_missing_keys_disables_after_hours(self):
        path = self._write(json.dumps({"latitude": 51.5}))  # no longitude
        self.assertEqual(d._load_coordinates(path), (None, None))

    def test_non_numeric_values_disable_after_hours(self):
        path = self._write(json.dumps({"latitude": "north", "longitude": -0.1}))
        self.assertEqual(d._load_coordinates(path), (None, None))

    def test_valid_config_returns_floats(self):
        path = self._write(json.dumps({"latitude": 51.5074, "longitude": -0.1278}))
        lat, lon = d._load_coordinates(path)
        self.assertAlmostEqual(lat, 51.5074)
        self.assertAlmostEqual(lon, -0.1278)


class ResolveDialectTests(unittest.TestCase):
    def test_unset_env_var_falls_back_to_default(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("FUZZYCLOCK_DIALECT", None)
            self.assertEqual(d._resolve_dialect(), d.DEFAULT_DIALECT)

    def test_known_dialect_is_returned(self):
        with mock.patch.dict(os.environ, {"FUZZYCLOCK_DIALECT": "shakespeare"}):
            self.assertEqual(d._resolve_dialect(), "shakespeare")

    def test_unknown_dialect_falls_back_with_warning(self):
        with mock.patch.dict(os.environ, {"FUZZYCLOCK_DIALECT": "pirate"}):
            with self.assertLogs("root", level="WARNING") as cm:
                self.assertEqual(d._resolve_dialect(), d.DEFAULT_DIALECT)
            self.assertTrue(any("pirate" in line for line in cm.output))


if __name__ == "__main__":
    unittest.main()
