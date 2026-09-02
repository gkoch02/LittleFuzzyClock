import argparse
from datetime import datetime

from PIL import Image, ImageDraw

from fuzzyclock_core import (
    AUTO_FRAME,
    DEFAULT_DIALECT,
    DEFAULT_FONT,
    DIALECTS,
    FONT_VARIANTS,
    FRAME_VARIANTS,
    RANDOM_FONT,
    pick_random_font,
    render_clock,
)


def _load_epd():
    """Import the Waveshare driver on demand. Returns the module, or None.

    Importing ``waveshare_epd`` is *not* side-effect free: ``epdconfig``
    instantiates its platform implementation at module scope, and on a Pi that
    constructor claims the GPIO pins via gpiozero. A plain import therefore
    fails outright whenever the daemon already owns those pins. Deferring the
    import to the hardware path is what keeps ``--dry-run`` genuinely
    hardware-free, so a preview works while fuzzyclock.service is running.

    The ``except`` is deliberately broad. The driver can fail in ways that are
    neither ImportError (library not installed) nor RuntimeError (no GPIO
    backend on non-Pi Linux): a busy pin surfaces as ``lgpio.error``, which is
    neither. Any failure here means the panel is not drivable, and the caller
    turns None into a clear SystemExit rather than a traceback.
    """
    try:
        from waveshare_epd import epd2in13_V4
    except Exception:
        return None
    return epd2in13_V4


def pin_time_to_today(time_str, today=None):
    """Combine an ``HH:MM`` string with today's date for --time previews.

    Returns a datetime on today's date (or ``today`` if supplied, for tests)
    at the parsed hour/minute. Using today's date instead of strptime's
    1900-01-01 default keeps the rendered date footer meaningful. Raises
    ValueError on malformed input; the CLI turns that into a clean argparse
    error instead of a traceback.
    """
    pinned = datetime.strptime(time_str, "%H:%M")
    base = today if today is not None else datetime.now()
    return base.replace(hour=pinned.hour, minute=pinned.minute, second=0, microsecond=0)


def draw_fuzzy_clock(
    dry_run=False,
    output="dry_run.png",
    dialect=DEFAULT_DIALECT,
    font=DEFAULT_FONT,
    frame=AUTO_FRAME,
    now=None,
):
    if dry_run:
        # 2.13" V4 display is 122×250 in portrait; landscape = 250×122
        width, height = 250, 122
        image = Image.new("1", (width, height), 255)
    else:
        epd_module = _load_epd()
        if epd_module is None:
            raise SystemExit(
                "waveshare_epd is not usable — it is either not installed, or its "
                "GPIO pins are held by another process (e.g. a running "
                "fuzzyclock.service). Use --dry-run for testing without hardware."
            )
        epd = epd_module.EPD()
        epd.init()
        # Swapped intentionally: the 2.13" display is 122×250 in portrait;
        # we use it in landscape, so logical width = physical height and vice versa.
        width, height = epd.height, epd.width
        image = Image.new("1", (width, height), 255)

    draw = ImageDraw.Draw(image)
    # `random` is a config sentinel rather than a real variant; resolve it to
    # a concrete vendored font for this one render. The daemon re-picks per
    # phrase change, but the CLI is one-shot so a single roll is enough.
    resolved_font = pick_random_font() if font == RANDOM_FONT else font
    render_clock(
        draw,
        width,
        height,
        now if now is not None else datetime.now(),
        font_variant=resolved_font,
        dialect=dialect,
        frame=frame,
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
        choices=sorted([RANDOM_FONT, *FONT_VARIANTS.keys()]),
        help=(
            f"Display font variant (default: {DEFAULT_FONT}). "
            f"Use {RANDOM_FONT!r} to pick a vendored variant at random."
        ),
    )
    parser.add_argument(
        "--frame",
        default=AUTO_FRAME,
        choices=sorted([AUTO_FRAME, *FRAME_VARIANTS.keys()]),
        help=(
            f"Border frame style (default: {AUTO_FRAME}). "
            f"{AUTO_FRAME!r} matches the frame to the active font's category."
        ),
    )
    parser.add_argument(
        "--time",
        default=None,
        metavar="HH:MM",
        help="Pin the clock to a fixed time for --dry-run previews (e.g. 09:15)",
    )
    args = parser.parse_args()
    now = None
    if args.time is not None:
        try:
            now = pin_time_to_today(args.time)
        except ValueError:
            parser.error(f"argument --time: invalid time {args.time!r} (expected HH:MM)")
    draw_fuzzy_clock(
        dry_run=args.dry_run,
        output=args.output,
        dialect=args.dialect,
        font=args.font,
        frame=args.frame,
        now=now,
    )
