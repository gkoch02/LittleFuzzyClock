"""Shared rendering logic for the fuzzy clock."""

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


def draw_border(draw, width, height, margin=4):
    r = 6
    draw.rectangle((margin, margin, width - margin, height - margin), outline=0, width=1)
    draw.ellipse((margin + 2, margin + 2, margin + 2 + r, margin + 2 + r), outline=0)
    draw.ellipse((width - margin - r - 2, margin + 2, width - margin - 2, margin + 2 + r), outline=0)
    draw.rectangle((margin + 2, height - margin - r - 2, margin + 2 + r, height - margin - 2), outline=0)
    draw.rectangle((width - margin - r - 2, height - margin - r - 2, width - margin - 2, height - margin - 2), outline=0)


def render_clock(draw, width, height, now, font_large, font_small, font_tiny, dialect=DEFAULT_DIALECT):
    """Draw the full clock face (border + phrase + hour + day line) onto `draw`."""
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

    draw_border(draw, width, height)
    draw.text(
        ((width - (phrase_bbox[2] - phrase_bbox[0])) // 2, y),
        phrase, font=phrase_font, fill=0,
    )
    draw.text(
        ((width - (hour_bbox[2] - hour_bbox[0])) // 2,
         y + (phrase_bbox[3] - phrase_bbox[1]) + 4),
        hour_str, font=hour_font, fill=0,
    )
    # Day line is pinned to the bottom edge as a fixed footer.
    draw.text(
        ((width - (day_bbox[2] - day_bbox[0])) // 2, height - day_bbox[3] - 6),
        day_line, font=font_tiny, fill=0,
    )
