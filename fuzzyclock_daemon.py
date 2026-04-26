import json
import logging
import os
import signal
import threading
import time
from datetime import UTC, datetime
from subprocess import run

from gpiozero import Button
from PIL import Image, ImageDraw

from fuzzyclock_core import (
    DEFAULT_DIALECT,
    DIALECTS,
    draw_border,
    load_font,
    render_clock,
    sun_times,
)
from waveshare_epd import epd2in13_V4

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

# === CONFIGURATION ===
GPIO_PIN = 3
UPDATE_INTERVAL = 300  # render the clock face every 5 minutes
TICK_INTERVAL = 60     # main loop wakes every minute to check mode transitions

# Render-failure thresholds. After RENDER_RETRY_REINIT consecutive failures
# we re-init the EPD and force a base-image reseed; after RENDER_RETRY_FATAL
# we exit and let systemd restart us cleanly (RestartSec=10 in the unit file).
RENDER_RETRY_REINIT = 3
RENDER_RETRY_FATAL = 10

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


CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fuzzyclock_config.json")


def _load_coordinates(path=CONFIG_PATH):
    """Read (latitude, longitude) from the JSON config file.

    Returns (None, None) if the file is missing or malformed; the daemon
    treats that as "after-hours mode disabled" rather than crashing.
    """
    try:
        with open(path) as f:
            cfg = json.load(f)
    except FileNotFoundError:
        logging.warning("Config file %s not found; after-hours mode disabled.", path)
        return None, None
    except (OSError, json.JSONDecodeError) as exc:
        logging.warning("Could not read %s (%s); after-hours mode disabled.", path, exc)
        return None, None
    try:
        return float(cfg["latitude"]), float(cfg["longitude"])
    except (KeyError, TypeError, ValueError) as exc:
        logging.warning(
            "Config file %s missing/invalid latitude or longitude (%s); "
            "after-hours mode disabled.", path, exc,
        )
        return None, None


DIALECT = _resolve_dialect()
# After-hours toggle is location-driven. Coordinates come from
# fuzzyclock_config.json next to this file; if it's missing or malformed,
# the feature stays off and the daemon falls back to plain day/night.
LATITUDE, LONGITUDE = _load_coordinates()
AFTER_HOURS_ENABLED = LATITUDE is not None and LONGITUDE is not None

# === FONTS ===
font_large = load_font(28)
font_small = load_font(22)
font_tiny  = load_font(14)
font_goodnight = load_font(24)

# === EPD LOCK — protects all SPI writes to the display ===
epd_lock = threading.Lock()

# Set by the SIGTERM/SIGINT handler so the main loop and the button-thread
# supervisor can break out of their waits and exit cleanly. Routing shutdown
# through an Event (instead of acquiring epd_lock inside the signal handler)
# avoids a deadlock if a signal arrives mid-render.
_stop_event = threading.Event()


def _sleep_to_next_tick(interval, now=None):
    """Return seconds until the next wall-clock multiple of `interval`.

    The result is always in (0, interval]. Sleeping for this duration keeps
    the daemon's ticks aligned with wall-clock minutes regardless of how
    long the previous render took, which eliminates cumulative drift.
    """
    now = now if now is not None else time.time()
    delay = interval - (now % interval)
    return delay if delay > 0 else interval


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
    now_utc = now.astimezone(UTC)
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
    while not _stop_event.is_set():
        button.wait_for_press()
        if _stop_event.is_set():
            return
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


def _button_supervisor(button, epd):
    """Run `button_listener` and restart it if it crashes.

    The button thread is daemonic, so a silent crash would leave the daemon
    running without any button input — and without a systemd restart, since
    the main process is still alive. The supervisor logs the exception and
    retries after a short backoff, exiting cleanly when `_stop_event` is set.
    """
    while not _stop_event.is_set():
        try:
            button_listener(button, epd)
        except Exception:
            logging.exception("button listener crashed; restarting in 10s")
            if _stop_event.wait(10):
                return


def main():
    epd = epd2in13_V4.EPD()
    epd.init()

    if AFTER_HOURS_ENABLED:
        logging.info(
            "After-hours mode enabled at lat=%.4f lon=%.4f.", LATITUDE, LONGITUDE,
        )
    else:
        logging.info(
            "After-hours mode disabled (set latitude/longitude in %s to enable).",
            CONFIG_PATH,
        )

    # Graceful shutdown on SIGTERM (systemd stop) or SIGINT (Ctrl-C). The
    # handler does no I/O and acquires no locks; the cleanup path runs in
    # the main loop below once it observes the event.
    def _handle_signal(signum, frame):
        logging.info("Signal %d received — exiting after current tick.", signum)
        _stop_event.set()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    # A failure here (missing GPIO, bus busy, running off-Pi for some reason)
    # shouldn't take down the clock. Log and run without the button.
    try:
        button = Button(GPIO_PIN, pull_up=True, bounce_time=0.05)
        threading.Thread(
            target=_button_supervisor, args=(button, epd), daemon=True,
        ).start()
    except Exception:
        logging.exception("Failed to initialise GPIO button; continuing without it.")

    # Seed the partial-refresh base image to match whichever mode we're starting in.
    initial_mode = current_mode()
    reset_base_image(epd, invert=(initial_mode == "after_hours"))

    last_state = None
    consecutive_failures = 0
    force_full = False

    while not _stop_event.is_set():
        mode = current_mode()
        if mode == "night":
            if last_state != "night":
                logging.info("Entering night mode.")
                try:
                    display_goodnight(epd)
                except Exception:
                    logging.exception("display_goodnight() failed")
        else:
            invert = mode == "after_hours"
            # Any transition into a clock-displaying mode (or a swap between
            # normal/inverted) leaves the partial-refresh base image stale, so
            # we re-seed it before the next displayPartial call. The very
            # first iteration is already covered by the seed above.
            if last_state is not None and last_state != mode:
                logging.info("Entering %s mode.", mode.replace("_", "-"))
                try:
                    reset_base_image(epd, invert=invert)
                except Exception:
                    logging.exception("reset_base_image() failed; will recover via re-init")
                    force_full = True

            # Render on mode change or on every 5-minute wall-clock boundary.
            # The 60s tick gives us ~1-minute mode-transition latency without
            # actually pushing pixels every minute.
            should_render = (
                last_state != mode
                or datetime.now().minute % 5 == 0
            )
            if should_render:
                try:
                    if force_full:
                        with epd_lock:
                            epd.init()
                        reset_base_image(epd, invert=invert)
                        force_full = False
                    draw_clock(epd, invert=invert)
                    consecutive_failures = 0
                except Exception:
                    consecutive_failures += 1
                    logging.exception(
                        "draw_clock() failed (%d/%d).",
                        consecutive_failures, RENDER_RETRY_FATAL,
                    )
                    if consecutive_failures >= RENDER_RETRY_FATAL:
                        logging.critical(
                            "draw_clock() failed %d times consecutively; "
                            "exiting for systemd to restart us.",
                            consecutive_failures,
                        )
                        break
                    if consecutive_failures >= RENDER_RETRY_REINIT:
                        force_full = True
        last_state = mode

        _stop_event.wait(timeout=_sleep_to_next_tick(TICK_INTERVAL))

    # Cooperative shutdown: put the panel to sleep so it doesn't burn in.
    logging.info("Main loop exited; sleeping display.")
    try:
        with epd_lock:
            epd.sleep()
    except Exception:
        logging.exception("epd.sleep() failed during shutdown")


if __name__ == "__main__":
    main()
