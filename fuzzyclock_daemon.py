import logging
import os
import signal
import sys
import time
import threading
from datetime import datetime, timezone
from PIL import Image, ImageDraw
from gpiozero import Button
from subprocess import run
from waveshare_epd import epd2in13_V4

from fuzzyclock_core import (
    DEFAULT_DIALECT,
    DIALECTS,
    draw_border,
    load_font,
    render_clock,
    sun_times,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

# === CONFIGURATION ===
GPIO_PIN = 3
UPDATE_INTERVAL = 300  # seconds (5 minutes)

# Day mode runs from DAY_START_HOUR up to (but not including) DAY_END_HOUR.
DAY_START_HOUR = 7
DAY_END_HOUR = 23

# Button press classification (seconds).
LONG_PRESS_SECONDS = 5.0        # hold this long → shutdown
SHORT_PRESS_MIN_SECONDS = 0.05  # anything shorter is debounce noise
SHORT_PRESS_MAX_SECONDS = 2.0   # anything between MAX and LONG_PRESS is ignored


def _resolve_dialect():
    requested = os.environ.get("FUZZYCLOCK_DIALECT", DEFAULT_DIALECT)
    if requested not in DIALECTS:
        logging.warning(
            "Unknown FUZZYCLOCK_DIALECT=%r; falling back to %r. Valid: %s",
            requested, DEFAULT_DIALECT, sorted(DIALECTS.keys()),
        )
        return DEFAULT_DIALECT
    return requested


def _resolve_float_env(name, default):
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        logging.warning("Ignoring %s=%r (not a number); using %s", name, raw, default)
        return default


DIALECT = _resolve_dialect()
# After-hours toggle is location-driven. Without coordinates we'd be guessing
# at sunset, so the feature is opt-in: set FUZZYCLOCK_LAT and FUZZYCLOCK_LON to
# enable. Both must be set or the daemon stays in normal day/night behaviour.
LATITUDE = _resolve_float_env("FUZZYCLOCK_LAT", None)
LONGITUDE = _resolve_float_env("FUZZYCLOCK_LON", None)
AFTER_HOURS_ENABLED = LATITUDE is not None and LONGITUDE is not None

# === FONTS ===
font_large = load_font(28)
font_small = load_font(22)
font_tiny  = load_font(14)
font_goodnight = load_font(24)

# === EPD LOCK — protects all SPI writes to the display ===
epd_lock = threading.Lock()


def current_mode(now=None):
    """Return one of "day", "after_hours", "night" for the given local time.

    Outside the wake window we're always in night/goodnight. Inside it, the sun
    decides between day (normal ink) and after-hours (inverted ink). When no
    coordinates are configured, after-hours is disabled and we always return
    "day" inside the wake window.
    """
    now = now or datetime.now().astimezone()
    if not (DAY_START_HOUR <= now.hour < DAY_END_HOUR):
        return "night"
    if not AFTER_HOURS_ENABLED:
        return "day"
    sunrise, sunset = sun_times(now.date(), LATITUDE, LONGITUDE)
    if sunrise is None or sunset is None:
        # Polar night / midnight sun: stick with day mode.
        return "day"
    now_utc = now.astimezone(timezone.utc)
    return "day" if sunrise <= now_utc <= sunset else "after_hours"


def reset_base_image(epd, invert=False):
    """Re-issue a blank base image for partial refresh.

    Required after any full epd.display() call (e.g. the goodnight screen) and
    whenever the foreground/background swap, since partial refresh diffs
    against the previously-set base image.
    """
    bg = 0 if invert else 255
    with epd_lock:
        base = Image.new('1', (epd.height, epd.width), bg)
        draw_border(ImageDraw.Draw(base), epd.height, epd.width, invert=invert)
        epd.displayPartBaseImage(epd.getbuffer(base.rotate(180)))


def display_goodnight(epd):
    width, height = epd.height, epd.width
    image = Image.new('1', (width, height), 255)
    draw = ImageDraw.Draw(image)

    text = "Goodnight"
    text_bbox = draw.textbbox((0, 0), text, font=font_goodnight)
    x = (width - (text_bbox[2] - text_bbox[0])) // 2
    y = (height - (text_bbox[3] - text_bbox[1])) // 2

    draw.rounded_rectangle(
        (10, 10, width - 10, height - 10),
        radius=15,
        outline=0,
        width=2,
    )
    draw.text((x, y), text, font=font_goodnight, fill=0)

    with epd_lock:
        epd.display(epd.getbuffer(image.rotate(180)))
    time.sleep(2)


def draw_clock(epd, invert=False):
    width, height = epd.height, epd.width
    bg = 0 if invert else 255
    image = Image.new('1', (width, height), bg)
    draw = ImageDraw.Draw(image)

    render_clock(
        draw, width, height, datetime.now(),
        font_large, font_small, font_tiny,
        dialect=DIALECT, invert=invert,
    )

    with epd_lock:
        epd.displayPartial(epd.getbuffer(image.rotate(180)))


def shutdown_procedure(epd):
    logging.info("Button long press detected — shutting down.")
    display_goodnight(epd)
    with epd_lock:
        epd.sleep()
    run(["shutdown", "-h", "now"])


def button_listener(button, epd):
    while True:
        button.wait_for_press()
        start = time.time()
        while button.is_pressed:
            time.sleep(0.01)
        duration = time.time() - start

        if duration >= LONG_PRESS_SECONDS:
            shutdown_procedure(epd)
        elif SHORT_PRESS_MIN_SECONDS < duration < SHORT_PRESS_MAX_SECONDS:
            logging.info("Short press — forcing update.")
            try:
                draw_clock(epd, invert=current_mode() == "after_hours")
            except Exception:
                logging.exception("draw_clock() failed on button press")
        else:
            logging.info("Ignored press (%.2f s)", duration)


def main():
    epd = epd2in13_V4.EPD()
    epd.init()
    width, height = epd.height, epd.width

    if AFTER_HOURS_ENABLED:
        logging.info(
            "After-hours mode enabled at lat=%.4f lon=%.4f.", LATITUDE, LONGITUDE,
        )
    else:
        logging.info(
            "After-hours mode disabled. Set FUZZYCLOCK_LAT and FUZZYCLOCK_LON to enable."
        )

    # Graceful shutdown on SIGTERM (systemd stop) or SIGINT (Ctrl-C)
    def _handle_signal(signum, frame):
        logging.info("Signal %d received — sleeping display and exiting.", signum)
        with epd_lock:
            epd.sleep()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    # Create the button in the main thread
    button = Button(GPIO_PIN, pull_up=True, bounce_time=0.05)

    # Seed the partial-refresh base image to match whichever mode we're starting in.
    initial_mode = current_mode()
    reset_base_image(epd, invert=(initial_mode == "after_hours"))

    # Start button monitoring thread
    threading.Thread(target=button_listener, args=(button, epd), daemon=True).start()

    last_state = None
    while True:
        mode = current_mode()
        if mode == "night":
            if last_state != "night":
                logging.info("Entering night mode.")
                display_goodnight(epd)
        else:
            invert = mode == "after_hours"
            # Any transition into a clock-displaying mode (or a swap between
            # normal/inverted) leaves the partial-refresh base image stale, so
            # we re-seed it before the next displayPartial call. The very
            # first iteration is already covered by the seed above.
            if last_state is not None and last_state != mode:
                logging.info("Entering %s mode.", mode.replace("_", "-"))
                reset_base_image(epd, invert=invert)
            try:
                draw_clock(epd, invert=invert)
            except Exception:
                logging.exception("draw_clock() failed in main loop")
        last_state = mode

        time.sleep(UPDATE_INTERVAL)


if __name__ == "__main__":
    main()
