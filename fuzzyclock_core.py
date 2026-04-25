"""Shared rendering logic for the fuzzy clock."""

import math
from datetime import datetime, timedelta, timezone

from PIL import ImageFont

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Raspberry Pi / Debian
    "/Library/Fonts/Arial Bold.ttf",                          # macOS
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",      # macOS (Ventura+)
    "/System/Library/Fonts/Helvetica.ttc",                    # macOS fallback
]

HOUR_WORDS = {
    1: "one", 2: "two", 3: "three", 4: "four",
    5: "five", 6: "six", 7: "seven", 8: "eight",
    9: "nine", 10: "ten", 11: "eleven", 12: "twelve",
}

DIALECTS = {
    "classic": {
        "phrases": [
            "just after", "a little past", "ten past", "quarter past",
            "twenty past", "twenty-five past", "half past",
            "twenty-five to", "twenty to", "quarter to", "ten to", "almost",
        ],
        "hours": HOUR_WORDS,
        "format_hour": lambda hour_word, is_pm: f"{hour_word} {'pm' if is_pm else 'am'}",
    },
    "shakespeare": {
        "phrases": [
            "'tis just past", "a moment past", "ten past", "'tis a quarter past",
            "twenty past", "twenty-five past", "'tis half past",
            "twenty-five 'fore", "twenty 'fore", "a quarter 'fore", "ten 'fore", "almost",
        ],
        "hours": HOUR_WORDS,
        # AM/PM is anachronistic; "of the clock" reads right at any hour.
        "format_hour": lambda hour_word, is_pm: f"{hour_word} of the clock",
    },
    "klingon": {
        "phrases": [
            "newly forged", "moments past", "ten past", "quarter past",
            "twenty past", "twenty-five past", "half past",
            "twenty-five 'til", "twenty 'til", "quarter 'til", "ten 'til",
            "battle nears",
        ],
        # Actual tlhIngan Hol numerals; "rep" is Klingon for "hour".
        "hours": {
            1: "wa'", 2: "cha'", 3: "wej", 4: "loS",
            5: "vagh", 6: "jav", 7: "Soch", 8: "chorgh",
            9: "Hut", 10: "wa'maH", 11: "wa'maH wa'", 12: "wa'maH cha'",
        },
        "format_hour": lambda hour_word, is_pm: f"{hour_word} rep",
    },
    "belter": {
        # Lang Belta creole: "to da" for "to the", "ke" as a sentence tag,
        # "savvy" for "you understand?". Belters keep maritime "bell" for time.
        "phrases": [
            "just past", "showxa pasa", "ten past", "quarter past",
            "twenty past", "twenty-five past", "half past",
            "twenty-five to da", "twenty to da", "quarter to da", "ten to da",
            "almost, ke",
        ],
        "hours": HOUR_WORDS,
        "format_hour": lambda hour_word, is_pm: f"{hour_word} bell, ya",
    },
}

DEFAULT_DIALECT = "classic"


def load_font(size):
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except IOError:
            continue
    raise SystemExit(
        "No usable font found. Tried:\n" + "\n".join(f"  {p}" for p in FONT_CANDIDATES)
    )


def fuzzy_time(hour, minute, dialect=DEFAULT_DIALECT):
    spec = DIALECTS[dialect]
    # Cap at 11 so minutes 57-59 stay as "almost [next hour]" rather than
    # wrapping back to index 0 ("just after [current hour]") via % 12.
    rounded = min(int(round(minute / 5.0)), 11)
    word = spec["phrases"][rounded]
    display_hour = hour if rounded <= 6 else (hour + 1) % 24
    hour_12 = display_hour % 12 or 12
    is_pm = display_hour >= 12
    return word, spec["format_hour"](spec["hours"][hour_12], is_pm)


def draw_border(draw, width, height, margin=4, invert=False):
    ink = 255 if invert else 0
    r = 6
    draw.rectangle((margin, margin, width - margin, height - margin), outline=ink, width=1)
    draw.ellipse((margin + 2, margin + 2, margin + 2 + r, margin + 2 + r), outline=ink)
    draw.ellipse((width - margin - r - 2, margin + 2, width - margin - 2, margin + 2 + r), outline=ink)
    draw.rectangle((margin + 2, height - margin - r - 2, margin + 2 + r, height - margin - 2), outline=ink)
    draw.rectangle((width - margin - r - 2, height - margin - r - 2, width - margin - 2, height - margin - 2), outline=ink)


def render_clock(draw, width, height, now, font_large, font_small, font_tiny,
                 dialect=DEFAULT_DIALECT, invert=False):
    """Draw the full clock face (border + phrase + hour + day line) onto `draw`.

    When `invert` is True the foreground is white (255) instead of black; the
    caller is responsible for filling the canvas with the matching background
    colour before calling this helper.
    """
    ink = 255 if invert else 0
    phrase, hour_str = fuzzy_time(now.hour, now.minute, dialect)
    day_line = now.strftime("%A, %b %d")

    phrase_font = font_small if len(phrase) > 12 else font_large
    hour_font = font_small if len(hour_str) > 12 else font_large
    phrase_bbox = draw.textbbox((0, 0), phrase, font=phrase_font)
    hour_bbox = draw.textbbox((0, 0), hour_str, font=hour_font)
    day_bbox = draw.textbbox((0, 0), day_line, font=font_tiny)

    total_height = (
        (phrase_bbox[3] - phrase_bbox[1]) +
        (hour_bbox[3] - hour_bbox[1]) +
        (day_bbox[3] - day_bbox[1]) + 10
    )
    y = (height - total_height) // 2

    draw_border(draw, width, height, invert=invert)
    draw.text(
        ((width - (phrase_bbox[2] - phrase_bbox[0])) // 2, y),
        phrase, font=phrase_font, fill=ink,
    )
    draw.text(
        ((width - (hour_bbox[2] - hour_bbox[0])) // 2,
         y + (phrase_bbox[3] - phrase_bbox[1]) + 4),
        hour_str, font=hour_font, fill=ink,
    )
    # Day line is pinned to the bottom edge as a fixed footer.
    draw.text(
        ((width - (day_bbox[2] - day_bbox[0])) // 2, height - day_bbox[3] - 6),
        day_line, font=font_tiny, fill=ink,
    )


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
    cos_h = (
        math.cos(math.radians(90.833)) / (math.cos(lat_rad) * math.cos(decl))
        - math.tan(lat_rad) * math.tan(decl)
    )
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
