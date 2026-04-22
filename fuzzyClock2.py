
import argparse
import time
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# Lazy-import the EPD driver so the script can run in --dry-run mode
# on machines without the waveshare library installed.
try:
    from waveshare_epd import epd2in13_V4
    EPD_AVAILABLE = True
except ImportError:
    EPD_AVAILABLE = False

# Font candidates in preference order (Linux/Pi first, then macOS fallbacks)
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Raspberry Pi / Debian
    "/Library/Fonts/Arial Bold.ttf",                          # macOS
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",      # macOS (Ventura+)
    "/System/Library/Fonts/Helvetica.ttc",                    # macOS fallback
]

def _load_font(size):
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except IOError:
            continue
    raise SystemExit(f"No usable font found. Tried:\n" + "\n".join(f"  {p}" for p in FONT_CANDIDATES))

font_large = _load_font(28)
font_small = _load_font(22)
font_tiny  = _load_font(14)

# Hour words
HOUR_WORDS = {
    1: "one", 2: "two", 3: "three", 4: "four",
    5: "five", 6: "six", 7: "seven", 8: "eight",
    9: "nine", 10: "ten", 11: "eleven", 12: "twelve"
}

def fuzzy_time(hour, minute):
    words = [
        "just after", "a little past", "ten past", "quarter past",
        "twenty past", "twenty-five past", "half past",
        "twenty-five to", "twenty to", "quarter to", "ten to", "almost"
    ]
    # Cap at 11 so minutes 57-59 stay as "almost [next hour]" rather than
    # wrapping back to index 0 ("just after [current hour]") via % 12.
    rounded = min(int(round(minute / 5.0)), 11)
    word = words[rounded]
    display_hour = hour if rounded <= 6 else (hour + 1) % 24
    hour_12 = display_hour % 12 or 12
    suffix = "AM" if display_hour < 12 else "PM"
    return word, f"{HOUR_WORDS[hour_12]} {suffix.lower()}"

def draw_bauhaus_border(draw, width, height, pad=4):
    # Outer border
    draw.rectangle((pad, pad, width - pad, height - pad), outline=0, width=1)

    # Geometric corner patterns
    r = 6
    draw.ellipse((pad + 2, pad + 2, pad + 2 + r, pad + 2 + r), outline=0)  # top-left circle
    draw.ellipse((width - pad - r - 2, pad + 2, width - pad - 2, pad + 2 + r), outline=0)  # top-right

    draw.rectangle((pad + 2, height - pad - r - 2, pad + 2 + r, height - pad - 2), outline=0)  # bottom-left square
    draw.rectangle((width - pad - r - 2, height - pad - r - 2, width - pad - 2, height - pad - 2), outline=0)  # bottom-right

def draw_fuzzy_clock(dry_run=False, output="dry_run.png"):
    if dry_run:
        # 2.13" V4 display is 122×250 in portrait; landscape = 250×122
        width, height = 250, 122
        image = Image.new('1', (width, height), 255)
        draw = ImageDraw.Draw(image)
    else:
        if not EPD_AVAILABLE:
            raise SystemExit(
                "waveshare_epd is not installed. Use --dry-run for testing without hardware."
            )
        epd = epd2in13_V4.EPD()
        epd.init()
        # Swapped intentionally: the 2.13" display is 122×250 in portrait;
        # we use it in landscape, so logical width = physical height and vice versa.
        width, height = epd.height, epd.width
        image = Image.new('1', (width, height), 255)
        draw = ImageDraw.Draw(image)

    now = datetime.now()
    phrase, hour_str = fuzzy_time(now.hour, now.minute)
    day_line = now.strftime("%A, %b %d")

    phrase_font = font_small if len(phrase) > 12 else font_large
    hour_font = font_large

    phrase_bbox = draw.textbbox((0, 0), phrase, font=phrase_font)
    hour_bbox = draw.textbbox((0, 0), hour_str, font=hour_font)
    day_bbox = draw.textbbox((0, 0), day_line, font=font_tiny)

    total_height = (
        (phrase_bbox[3] - phrase_bbox[1]) +
        (hour_bbox[3] - hour_bbox[1]) +
        (day_bbox[3] - day_bbox[1]) + 10
    )
    y = (height - total_height) // 2

    draw_bauhaus_border(draw, width, height)

    phrase_w = phrase_bbox[2] - phrase_bbox[0]
    hour_w = hour_bbox[2] - hour_bbox[0]
    day_w = day_bbox[2] - day_bbox[0]

    draw.text(((width - phrase_w) // 2, y), phrase, font=phrase_font, fill=0)
    draw.text(((width - hour_w) // 2, y + (phrase_bbox[3] - phrase_bbox[1]) + 4), hour_str, font=hour_font, fill=0)
    # Day line is pinned to the bottom edge rather than included in the
    # centered block, acting as a fixed footer.
    draw.text(((width - day_w) // 2, height - day_bbox[3] - 6), day_line, font=font_tiny, fill=0)

    if dry_run:
        image.save(output)
        print(f"Dry-run: saved to {output}")
    else:
        # Rotate 180° to correct for the display being mounted upside-down.
        image = image.rotate(180)
        epd.display(epd.getbuffer(image))
        epd.sleep()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fuzzy clock for Waveshare e-ink display")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Render to a PNG instead of the e-ink display (no hardware required)"
    )
    parser.add_argument(
        "--output", default="dry_run.png", metavar="FILE",
        help="Output PNG path for --dry-run (default: dry_run.png)"
    )
    args = parser.parse_args()
    draw_fuzzy_clock(dry_run=args.dry_run, output=args.output)
