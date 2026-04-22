import argparse
from datetime import datetime
from PIL import Image, ImageDraw

from fuzzyclock_core import load_font, render_clock

# Lazy-import the EPD driver so the script can run in --dry-run mode on
# machines without the waveshare library — or without Pi hardware. The
# driver raises RuntimeError (not ImportError) on non-Pi Linux when it
# can't find the GPIO backend, so catch that too.
try:
    from waveshare_epd import epd2in13_V4
    EPD_AVAILABLE = True
except (ImportError, RuntimeError):
    EPD_AVAILABLE = False

font_large = load_font(28)
font_small = load_font(22)
font_tiny  = load_font(14)


def draw_fuzzy_clock(dry_run=False, output="dry_run.png"):
    if dry_run:
        # 2.13" V4 display is 122×250 in portrait; landscape = 250×122
        width, height = 250, 122
        image = Image.new('1', (width, height), 255)
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
    render_clock(draw, width, height, datetime.now(), font_large, font_small, font_tiny)

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
