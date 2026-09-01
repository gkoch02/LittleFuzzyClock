"""Tests for fuzzyclock_core.sun_times.

The NOAA approximation isn't second-accurate, but it should land within a
few minutes of published sunrise/sunset values away from the poles. We pin
a handful of known dates and assert the prediction is close, plus check the
polar-night / midnight-sun branches.

Run with: python3 -m unittest test_sun
"""

import unittest
from datetime import date, datetime, timezone

from fuzzyclock_core import sun_times


def _minutes_diff(a, b):
    return abs((a - b).total_seconds()) / 60.0


class SunTimesTests(unittest.TestCase):
    # Reference data from timeanddate.com / NOAA. Times are UTC.
    # tolerance covers the ~minute-or-two error of the simplified model.
    TOLERANCE_MIN = 5

    def _assert_close(self, predicted, expected_utc):
        self.assertLessEqual(
            _minutes_diff(predicted, expected_utc),
            self.TOLERANCE_MIN,
            f"predicted {predicted.isoformat()} vs expected {expected_utc.isoformat()}",
        )

    def test_san_francisco_summer_solstice(self):
        # 2024-06-20 SF: sunrise ~05:48 PDT (12:48 UTC), sunset ~20:34 PDT (03:34 UTC next day).
        sunrise, sunset = sun_times(date(2024, 6, 20), 37.7749, -122.4194)
        self._assert_close(sunrise, datetime(2024, 6, 20, 12, 48, tzinfo=timezone.utc))
        self._assert_close(sunset, datetime(2024, 6, 21, 3, 34, tzinfo=timezone.utc))

    def test_london_winter_solstice(self):
        # 2024-12-21 London: sunrise ~08:04 UTC, sunset ~15:53 UTC.
        sunrise, sunset = sun_times(date(2024, 12, 21), 51.5074, -0.1278)
        self._assert_close(sunrise, datetime(2024, 12, 21, 8, 4, tzinfo=timezone.utc))
        self._assert_close(sunset, datetime(2024, 12, 21, 15, 53, tzinfo=timezone.utc))

    def test_equator_equinox_is_roughly_twelve_hours(self):
        sunrise, sunset = sun_times(date(2024, 3, 20), 0.0, 0.0)
        day_length_min = (sunset - sunrise).total_seconds() / 60.0
        self.assertAlmostEqual(day_length_min, 12 * 60, delta=15)

    def test_polar_night_returns_none(self):
        # Far above the Arctic Circle in mid-December → sun never rises.
        sunrise, sunset = sun_times(date(2024, 12, 21), 80.0, 0.0)
        self.assertIsNone(sunrise)
        self.assertIsNone(sunset)

    def test_midnight_sun_returns_none(self):
        # Far above the Arctic Circle in mid-June → sun never sets.
        sunrise, sunset = sun_times(date(2024, 6, 21), 80.0, 0.0)
        self.assertIsNone(sunrise)
        self.assertIsNone(sunset)

    def test_returns_aware_utc_datetimes(self):
        sunrise, sunset = sun_times(date(2024, 4, 25), 37.7749, -122.4194)
        self.assertIsNotNone(sunrise.tzinfo)
        self.assertIsNotNone(sunset.tzinfo)
        self.assertEqual(sunrise.utcoffset().total_seconds(), 0)
        self.assertEqual(sunset.utcoffset().total_seconds(), 0)

    def test_sunset_is_after_sunrise(self):
        for d in (date(2024, 1, 15), date(2024, 4, 25), date(2024, 7, 4), date(2024, 10, 1)):
            sunrise, sunset = sun_times(d, 37.7749, -122.4194)
            self.assertGreater(sunset, sunrise, f"sunset before sunrise on {d}")


if __name__ == "__main__":
    unittest.main()
