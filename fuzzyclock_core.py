"""Shared rendering logic for the fuzzy clock."""

import math
import os
from datetime import datetime, timedelta, timezone

from PIL import ImageFont

# Repo-vendored fonts live under <repo>/fonts/. Variants can prefix this onto
# their candidate list to let users drop a custom .ttf in without touching apt.
_VENDORED_FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Raspberry Pi / Debian
    "/Library/Fonts/Arial Bold.ttf",  # macOS
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",  # macOS (Ventura+)
    "/System/Library/Fonts/Helvetica.ttc",  # macOS fallback
]

# Selectable display fonts. Each variant maps to an ordered list of candidate
# paths: load_font() walks them and uses the first that PIL can open. Pi-side
# paths come first; macOS fallbacks (the closest stock equivalent) keep dev
# renders working off-Pi for every variant. The `dejavu` variant aliases the
# legacy `FONT_CANDIDATES` list so existing imports stay byte-identical.
FONT_VARIANTS = {
    "dejavu": FONT_CANDIDATES,
    "dejavu-serif": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",  # fonts-dejavu
        "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
        "/Library/Fonts/Times New Roman Bold.ttf",
    ],
    "liberation-serif": [
        "/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf",  # fonts-liberation2
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",  # older Debian layout
        "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
    ],
    "roboto-slab": [
        # fonts-roboto-slab Ubuntu/recent path (.otf), Bookworm path (.ttf), older layout
        "/usr/share/fonts/opentype/roboto/slab/RobotoSlab-Bold.otf",
        "/usr/share/fonts/truetype/roboto/slab/RobotoSlab-Bold.ttf",
        "/usr/share/fonts/truetype/roboto-slab/RobotoSlab-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
    ],
    "cantarell": [
        "/usr/share/fonts/opentype/cantarell/Cantarell-Bold.otf",  # fonts-cantarell (Ubuntu/recent)
        "/usr/share/fonts/cantarell/Cantarell-Bold.otf",  # fonts-cantarell (older Debian)
        "/System/Library/Fonts/Supplemental/Verdana Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "ubuntu": [
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",  # fonts-ubuntu
        "/System/Library/Fonts/Supplemental/Trebuchet MS Bold.ttf",
    ],
    "jetbrains-mono": [
        "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf",  # fonts-jetbrains-mono
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Monaco.ttf",
    ],
    "fredoka": [
        # Vendored first so users can drop a custom Fredoka.ttf under fonts/
        # without waiting on apt or upstream variants.
        os.path.join(_VENDORED_FONT_DIR, "Fredoka.ttf"),
        "/usr/share/fonts/truetype/fredoka/Fredoka-VariableFont_wdth,wght.ttf",  # fonts-fredoka
        "/usr/share/fonts/truetype/fredoka-one/FredokaOne-Regular.ttf",  # fonts-fredoka-one (older)
        "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",
    ],
}

DEFAULT_FONT = "dejavu"

HOUR_WORDS = {
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
    11: "eleven",
    12: "twelve",
}

DIALECTS = {
    "classic": {
        "phrases": [
            "just after",
            "a little past",
            "ten past",
            "quarter past",
            "twenty past",
            "twenty-five past",
            "half past",
            "twenty-five to",
            "twenty to",
            "quarter to",
            "ten to",
            "almost",
        ],
        "hours": HOUR_WORDS,
        "format_hour": lambda hour_word, is_pm: f"{hour_word} {'pm' if is_pm else 'am'}",
    },
    "shakespeare": {
        "phrases": [
            "'tis just past",
            "a moment past",
            "ten past",
            "'tis a quarter past",
            "twenty past",
            "twenty-five past",
            "'tis half past",
            "twenty-five 'fore",
            "twenty 'fore",
            "a quarter 'fore",
            "ten 'fore",
            "almost",
        ],
        "hours": HOUR_WORDS,
        # AM/PM is anachronistic; "of the clock" reads right at any hour.
        "format_hour": lambda hour_word, is_pm: f"{hour_word} of the clock",
    },
    "klingon": {
        "phrases": [
            "newly forged",
            "moments past",
            "ten past",
            "quarter past",
            "twenty past",
            "twenty-five past",
            "half past",
            "twenty-five 'til",
            "twenty 'til",
            "quarter 'til",
            "ten 'til",
            "battle nears",
        ],
        # Actual tlhIngan Hol numerals; "rep" is Klingon for "hour".
        "hours": {
            1: "wa'",
            2: "cha'",
            3: "wej",
            4: "loS",
            5: "vagh",
            6: "jav",
            7: "Soch",
            8: "chorgh",
            9: "Hut",
            10: "wa'maH",
            11: "wa'maH wa'",
            12: "wa'maH cha'",
        },
        "format_hour": lambda hour_word, is_pm: f"{hour_word} rep",
    },
    "belter": {
        # Lang Belta creole: "to da" for "to the", "ke" as a sentence tag,
        # "savvy" for "you understand?". Belters keep maritime "bell" for time.
        "phrases": [
            "just past",
            "showxa pasa",
            "ten past",
            "quarter past",
            "twenty past",
            "twenty-five past",
            "half past",
            "twenty-five to da",
            "twenty to da",
            "quarter to da",
            "ten to da",
            "almost, ke",
        ],
        "hours": HOUR_WORDS,
        "format_hour": lambda hour_word, is_pm: f"{hour_word} bell, ya",
    },
    "german": {
        # Standard High German fuzzy time. "halb [hour]" means "half-to
        # [hour]" — 9:30 reads "halb zehn" (half ten), referencing the *next*
        # hour. The 25-past and 35-past slots ("fünf vor halb", "fünf nach
        # halb") share the same anchor, so this dialect bumps
        # `hour_advance_at` down to 5 to advance the displayed hour starting
        # at index 5 instead of 7.
        # Regional variants (Swiss "viertel ab", Austrian etc.) intentionally
        # not applied — keep this entry as the de-DE/standard form.
        "phrases": [
            "kurz nach",
            "fünf nach",
            "zehn nach",
            "viertel nach",
            "zwanzig nach",
            "fünf vor halb",
            "halb",
            "fünf nach halb",
            "zwanzig vor",
            "viertel vor",
            "zehn vor",
            "kurz vor",
        ],
        "hours": {
            1: "eins",
            2: "zwei",
            3: "drei",
            4: "vier",
            5: "fünf",
            6: "sechs",
            7: "sieben",
            8: "acht",
            9: "neun",
            10: "zehn",
            11: "elf",
            12: "zwölf",
        },
        "hour_advance_at": 5,
        "format_hour": lambda hour_word, is_pm: hour_word,
    },
    "hal": {
        # HAL 9000 — terse, all-caps, mission-control T-minus cadence.
        # "MIDPOINT" and "IMMINENT" replace the T±N readout at the half-hour
        # and top-of-hour for the same reason HAL drops into clipped
        # declaratives in 2001: it sounds more inevitable that way.
        # Hours render as 24h numeric ("0900 HOURS" / "2100 HOURS") so the
        # mission-control voice stays consistent and the AM/PM signal isn't
        # silently dropped — important for a dialect that's explicitly
        # military timekeeping.
        "phrases": [
            "ON THE MARK",
            "T+5 MINUTES",
            "T+10 MINUTES",
            "T+15 MINUTES",
            "T+20 MINUTES",
            "T+25 MINUTES",
            "MIDPOINT",
            "T-25 MINUTES",
            "T-20 MINUTES",
            "T-15 MINUTES",
            "T-10 MINUTES",
            "IMMINENT",
        ],
        "hours": {i: str(i) for i in range(1, 13)},
        "format_hour": lambda hour_word, is_pm: (
            f"{((int(hour_word) % 12) + (12 if is_pm else 0)):02d}00 HOURS"
        ),
    },
    "cthulhu": {
        # Lovecraftian dread. The atmosphere lives on the hour line — every
        # reading is "the [ordinal] hour" — and on two flavor phrases:
        # "newly woken" / "moments past" at the start of an hour, and the
        # iconic "the stars are right" at the top of the next one (the
        # Lovecraft phrase precedes Cthulhu's awakening from R'lyeh).
        # The middle indices stay generic so the dread accents land where
        # they matter; "the eleventh hour" doubles as the idiom for "too
        # late" on every 10:30+ reading.
        "phrases": [
            "newly woken",
            "moments past",
            "ten past",
            "quarter past",
            "twenty past",
            "twenty-five past",
            "the half-hour",
            "twenty-five 'fore",
            "twenty 'fore",
            "quarter 'fore",
            "ten 'fore",
            "the stars are right",
        ],
        "hours": {
            1: "first",
            2: "second",
            3: "third",
            4: "fourth",
            5: "fifth",
            6: "sixth",
            7: "seventh",
            8: "eighth",
            9: "ninth",
            10: "tenth",
            11: "eleventh",
            12: "twelfth",
        },
        "format_hour": lambda hour_word, is_pm: f"the {hour_word} hour",
    },
    "latin": {
        # Latin-inspired fuzzy time. Hours render as Roman numerals — the
        # iconic clock-face form — with the literal "a.m."/"p.m." (ante/post
        # meridiem) abbreviations as an etymology Easter egg. Phrases use
        # Latin time prepositions: "post" (after), "ante" (before), "fere"
        # (almost), "modo" (just/recently). Grammar is loose because Latin
        # word order resists the phrase/hour split, but every word is real.
        # (We use IV not IIII; the latter is a clock-face convention, not a
        # general Roman numeral one.)
        "phrases": [
            "modo post",
            "quinque post",
            "decem post",
            "quadrans post",
            "viginti post",
            "viginti quinque post",
            "media post",
            "viginti quinque ante",
            "viginti ante",
            "quadrans ante",
            "decem ante",
            "fere",
        ],
        "hours": {
            1: "I",
            2: "II",
            3: "III",
            4: "IV",
            5: "V",
            6: "VI",
            7: "VII",
            8: "VIII",
            9: "IX",
            10: "X",
            11: "XI",
            12: "XII",
        },
        "format_hour": lambda hw, is_pm: f"hora {hw} {'p.m.' if is_pm else 'a.m.'}",
    },
}

DEFAULT_DIALECT = "classic"


def _validate_dialects(dialects):
    """Reject dialects with an out-of-range `hour_advance_at`.

    `hour_advance_at` controls when the displayed hour flips from current to
    next. It must stay <= 11 so the index-11 ("almost") slot still advances —
    otherwise minutes 57-59 wrap back to "almost [current hour]" via % 12,
    which is the bug the min(..., 11) cap in fuzzy_time exists to prevent.
    """
    for name, spec in dialects.items():
        adv = spec.get("hour_advance_at", 7)
        if not 1 <= adv <= 11:
            raise ValueError(
                f"Dialect {name!r} has invalid hour_advance_at={adv}; "
                "must be in 1..11 to preserve the almost-next-hour invariant."
            )


_validate_dialects(DIALECTS)


def load_font(size, variant=None):
    """Load a TrueType/OpenType font at `size` from a registered variant.

    `variant=None` walks the legacy FONT_CANDIDATES list (DejaVu Sans Bold +
    macOS fallbacks) — preserved for backward compat with code that doesn't
    care which variant. A named variant must exist in FONT_VARIANTS; unknown
    keys raise KeyError (programming-bug guard — the daemon validates upstream
    via _resolve_font and falls back gracefully on user input).

    For variable fonts (e.g. Fredoka.ttf, which carries a wght axis), we
    activate the "Bold" named instance so weight matches the static-Bold
    static fonts the other variants ship as — otherwise PIL renders at the
    default axis values (Light/Regular), which looks wispy on e-ink and
    hides the variant's character. Static fonts raise OSError on the call
    and we silently skip it.

    Raises SystemExit listing the variant's tried paths when none load. We
    fail loud rather than letting PIL silently fall back to its default
    bitmap font, which would render a subtly-wrong clock face.
    """
    if variant is None:
        candidates = FONT_CANDIDATES
        label = "default"
    else:
        candidates = FONT_VARIANTS[variant]
        label = variant
    for path in candidates:
        try:
            font = ImageFont.truetype(path, size)
        except OSError:
            continue
        try:
            font.set_variation_by_name("Bold")
        except (OSError, AttributeError):
            pass
        return font
    raise SystemExit(
        f"No usable font found for variant {label!r}. Tried:\n"
        + "\n".join(f"  {p}" for p in candidates)
    )


def fuzzy_time(hour, minute, dialect=DEFAULT_DIALECT):
    spec = DIALECTS[dialect]
    # Cap at 11 so minutes 57-59 stay as "almost [next hour]" rather than
    # wrapping back to index 0 ("just after [current hour]") via % 12.
    rounded = min(int(round(minute / 5.0)), 11)
    word = spec["phrases"][rounded]
    # Most dialects flip to the next hour at 35-past ("twenty-five to ten");
    # German flips at 25-past so "halb zehn" / "fünf vor halb zehn" anchor on
    # the upcoming hour as native speakers expect.
    advance_at = spec.get("hour_advance_at", 7)
    display_hour = hour if rounded < advance_at else (hour + 1) % 24
    hour_12 = display_hour % 12 or 12
    is_pm = display_hour >= 12
    return word, spec["format_hour"](spec["hours"][hour_12], is_pm)


def draw_border(draw, width, height, margin=5, invert=False):
    """Frame the canvas with four symmetric L-shaped corner ticks.

    Replaces the previous outline+mixed-corner design. Each tick is a 1 px
    right-angle bracket with ~10 px arms, inset `margin` from the edge.
    """
    ink = 255 if invert else 0
    arm = 10
    right = width - margin - 1
    bottom = height - margin - 1
    # Top-left
    draw.line((margin, margin, margin + arm, margin), fill=ink, width=1)
    draw.line((margin, margin, margin, margin + arm), fill=ink, width=1)
    # Top-right
    draw.line((right - arm, margin, right, margin), fill=ink, width=1)
    draw.line((right, margin, right, margin + arm), fill=ink, width=1)
    # Bottom-left
    draw.line((margin, bottom, margin + arm, bottom), fill=ink, width=1)
    draw.line((margin, bottom - arm, margin, bottom), fill=ink, width=1)
    # Bottom-right
    draw.line((right - arm, bottom, right, bottom), fill=ink, width=1)
    draw.line((right, bottom - arm, right, bottom), fill=ink, width=1)


def draw_day_progress(draw, width, height, progress, line_y, invert=False, inset=10):
    """Draw a horizon line at `line_y` with a 3x3 mark at `progress` along it.

    `progress` is a float in [0, 1] (clamped) or None (no-op). The line spans
    from `inset` to `width - inset`, staying clear of the corner ticks. The
    mark is centered on the line, so 0.0 puts it flush with the inset edge
    and 1.0 puts it flush with the opposite inset.
    """
    if progress is None:
        return
    progress = max(0.0, min(1.0, progress))
    ink = 255 if invert else 0
    left, right = inset, width - inset
    draw.line((left, line_y, right, line_y), fill=ink, width=1)
    mark_x = left + int(round(progress * (right - left)))
    draw.rectangle(
        (mark_x - 1, line_y - 1, mark_x + 1, line_y + 1),
        fill=ink,
    )


def render_clock(
    draw,
    width,
    height,
    now,
    font_large,
    font_small,
    font_tiny,
    dialect=DEFAULT_DIALECT,
    invert=False,
    font_phrase=None,
    progress=None,
):
    """Draw the full clock face (frame + phrase + hour + date + optional
    day-progress horizon) onto `draw`.

    Typography hierarchy: phrase is the smaller "kicker" line, hour is the
    focal display. Pass `font_phrase` (typically smaller than `font_small`)
    to make the kicker/headline contrast more pronounced; without it the
    phrase falls back to `font_small`. The hour stays on `font_large` unless
    its string is too wide to fit, in which case it drops to `font_small`.

    `progress` is a float in [0, 1] showing where `now` sits between today's
    sunrise and sunset; when supplied, a thin horizon line and a small mark
    are drawn just above the date footer. None disables the indicator —
    callers without coordinates configured (or in polar night/midnight sun)
    pass None and the layout collapses gracefully.

    When `invert` is True the foreground is white (255) instead of black;
    the caller is responsible for filling the canvas with the matching
    background colour before calling this helper.
    """
    ink = 255 if invert else 0
    phrase, hour_str = fuzzy_time(now.hour, now.minute, dialect)
    day_line = now.strftime("%A, %b %d")

    phrase_font = font_phrase if font_phrase is not None else font_small
    # When a dedicated phrase font is in use, an unusually long phrase
    # (Shakespeare's "'tis a quarter past") would still fit, but the extra
    # safety net keeps custom variants with wide metrics from overflowing.
    if font_phrase is not None and len(phrase) > 14:
        phrase_font = font_tiny
    hour_font = font_small if len(hour_str) > 12 else font_large

    phrase_bbox = draw.textbbox((0, 0), phrase, font=phrase_font)
    hour_bbox = draw.textbbox((0, 0), hour_str, font=hour_font)
    day_bbox = draw.textbbox((0, 0), day_line, font=font_tiny)
    phrase_h = phrase_bbox[3] - phrase_bbox[1]
    hour_h = hour_bbox[3] - hour_bbox[1]
    day_h = day_bbox[3] - day_bbox[1]

    draw_border(draw, width, height, invert=invert)

    # Date stays pinned 6 px from the bottom; the horizon (if any) sits 4 px
    # above the date's top. The phrase+hour stack is vertically centered in
    # whatever space remains between the top corner ticks and the horizon.
    date_y = height - day_h - 6
    horizon_y = date_y - 4
    text_top = 8
    text_bottom = horizon_y - 4 if progress is not None else date_y - 4
    text_block_h = phrase_h + hour_h + 2
    y = text_top + max(0, (text_bottom - text_top - text_block_h) // 2)

    draw.text(
        ((width - (phrase_bbox[2] - phrase_bbox[0])) // 2, y),
        phrase,
        font=phrase_font,
        fill=ink,
    )
    draw.text(
        ((width - (hour_bbox[2] - hour_bbox[0])) // 2, y + phrase_h + 2),
        hour_str,
        font=hour_font,
        fill=ink,
    )
    draw.text(
        ((width - (day_bbox[2] - day_bbox[0])) // 2, date_y),
        day_line,
        font=font_tiny,
        fill=ink,
    )
    draw_day_progress(draw, width, height, progress, horizon_y, invert=invert)


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
