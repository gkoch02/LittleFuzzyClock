"""Sunrise/sunset approximation (NOAA simplified solar-position equation).

Self-contained: depends only on the standard library, not on any other
fuzzyclock module.
"""

import math
from datetime import datetime, timedelta, timezone


def sun_times(date, latitude, longitude):
    """Approximate sunrise and sunset for `date` at (latitude, longitude).

    Returns aware UTC datetimes (sunrise, sunset). `date` may be a `date` or
    `datetime`; only the calendar day is used. Returns (None, None) for polar
    night / midnight sun (the sun never crosses the horizon that day).

    Implementation follows NOAA's simplified solar position algorithm. Accuracy
    is within ~1 minute outside polar regions, which is plenty for "switch the
    clock theme around dusk".
    """
    n = date.timetuple().tm_yday
    # Fractional year (radians)
    gamma = 2 * math.pi / 365 * (n - 1)
    # Equation of time (minutes)
    eqtime = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )
    # Solar declination (radians)
    decl = (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma)
        + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma)
        + 0.00148 * math.sin(3 * gamma)
    )
    lat_rad = math.radians(latitude)
    # 90.833° accounts for atmospheric refraction + the sun's apparent radius.
    cos_h = math.cos(math.radians(90.833)) / (math.cos(lat_rad) * math.cos(decl)) - math.tan(
        lat_rad
    ) * math.tan(decl)
    if cos_h > 1 or cos_h < -1:
        return None, None
    h_deg = math.degrees(math.acos(cos_h))

    # Times come out in minutes-from-UTC-midnight.
    sunrise_min = 720 - 4 * (longitude + h_deg) - eqtime
    sunset_min = 720 - 4 * (longitude - h_deg) - eqtime

    base = datetime(date.year, date.month, date.day, tzinfo=timezone.utc)
    return (
        base + timedelta(minutes=sunrise_min),
        base + timedelta(minutes=sunset_min),
    )
