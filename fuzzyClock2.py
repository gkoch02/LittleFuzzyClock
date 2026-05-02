import argparse
from datetime import datetime, timezone

from PIL import Image, ImageDraw

from fuzzyclock_core import (
    DEFAULT_DIALECT,
    DEFAULT_FONT,
    DIALECTS,
    FONT_VARIANTS,
    load_font,
    render_clock,
    sun_times,
)

# Lazy-import the EPD driver so the script can run in --dry-run mode on
# machines without the waveshare library — or without Pi hardware. The
# driver raises RuntimeError (not ImportError) on non-Pi Linux when it
# can't find the GPIO backend, so catch that too.
try:
    from waveshare_epd import epd2in13_V4

    EPD_AVAILABLE = True
except (ImportError, RuntimeError):
    EPD_AVAILABLE = False


def _compute_progress(latitude, longitude):
    """Return today's day-progress fraction in [0, 1] or None.

    Mirrors the daemon's `_current_progress`: None when coordinates are
    missing or when the sun never crosses the horizon (polar night/midnight
    sun), 0.0 before sunrise, 1.0 after sunset.
    """
    if latitude is None or longitude is None:
        return None
    now = datetime.now().astimezone()
    sunrise, sunset = sun_times(now.date(), latitude, longitude)
    if sunrise is None or sunset is None or sunset <= sunrise:
        return None
    now_utc = now.astimezone(timezone.utc)
    span = (sunset - sunrise).total_seconds()
    elapsed = (now_utc - sunrise).total_seconds()
    return max(0.0, min(1.0, elapsed / span))


def draw_fuzzy_clock(
    dry_run=False,
    output="dry_run.png",
    dialect=DEFAULT_DIALECT,
    font=DEFAULT_FONT,
    latitude=None,
    longitude=None,
):
    # Fonts are loaded inside the entry function (rather than at module import)
    # so `import fuzzyClock2` doesn't SystemExit on hosts without DejaVu.
    font_large = load_font(28, variant=font)
    font_small = load_font(22, variant=font)
    font_tiny = load_font(14, variant=font)
    font_phrase = load_font(18, variant=font)

    if dry_run:
        # 2.13" V4 display is 122×250 in portrait; landscape = 250×122
        width, height = 250, 122
        image = Image.new("1", (width, height), 255)
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
        image = Image.new("1", (width, height), 255)

    draw = ImageDraw.Draw(image)
    render_clock(
        draw,
        width,
        height,
        datetime.now(),
        font_large,
        font_small,
        font_tiny,
        dialect=dialect,
        font_phrase=font_phrase,
        progress=_compute_progress(latitude, longitude),
    )

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
        "--dry-run",
        action="store_true",
        help="Render to a PNG instead of the e-ink display (no hardware required)",
    )
    parser.add_argument(
        "--output",
        default="dry_run.png",
        metavar="FILE",
        help="Output PNG path for --dry-run (default: dry_run.png)",
    )
    parser.add_argument(
        "--dialect",
        default=DEFAULT_DIALECT,
        choices=sorted(DIALECTS.keys()),
        help=f"Phrasing personality (default: {DEFAULT_DIALECT})",
    )
    parser.add_argument(
        "--font",
        default=DEFAULT_FONT,
        choices=sorted(FONT_VARIANTS.keys()),
        help=f"Display font variant (default: {DEFAULT_FONT})",
    )
    parser.add_argument(
        "--lat",
        type=float,
        default=None,
        help="Latitude for the day-progress indicator (omit to disable)",
    )
    parser.add_argument(
        "--lon",
        type=float,
        default=None,
        help="Longitude for the day-progress indicator (omit to disable)",
    )
    args = parser.parse_args()
    draw_fuzzy_clock(
        dry_run=args.dry_run,
        output=args.output,
        dialect=args.dialect,
        font=args.font,
        latitude=args.lat,
        longitude=args.lon,
    )
