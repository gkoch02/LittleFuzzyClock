import logging
import os
import signal
import sys
import time
import threading
from datetime import datetime
from PIL import Image, ImageDraw
from gpiozero import Button
from subprocess import run
from waveshare_epd import epd2in13_V4

from fuzzyclock_core import DEFAULT_DIALECT, DIALECTS, draw_border, load_font, render_clock

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


DIALECT = _resolve_dialect()

# === FONTS ===
font_large = load_font(28)
font_small = load_font(22)
font_tiny  = load_font(14)
font_goodnight = load_font(24)

# === EPD LOCK — protects all SPI writes to the display ===
epd_lock = threading.Lock()


def _blank_base_image(epd):
    """Return a blank white image sized for the display (pre-rotated)."""
    width, height = epd.height, epd.width
    img = Image.new('1', (width, height), 255)
    return img


def reset_base_image(epd):
    """Re-issue a blank base image for partial refresh (needed after a full display() call)."""
    with epd_lock:
        base = _blank_base_image(epd)
        draw_border(ImageDraw.Draw(base), epd.height, epd.width)
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


def draw_clock(epd):
    width, height = epd.height, epd.width
    image = Image.new('1', (width, height), 255)
    draw = ImageDraw.Draw(image)

    render_clock(draw, width, height, datetime.now(), font_large, font_small, font_tiny, dialect=DIALECT)

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
                draw_clock(epd)
            except Exception:
                logging.exception("draw_clock() failed on button press")
        else:
            logging.info("Ignored press (%.2f s)", duration)


def main():
    epd = epd2in13_V4.EPD()
    epd.init()
    width, height = epd.height, epd.width

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

    # Clear display and draw initial border as base image for partial refresh
    base_image = Image.new('1', (width, height), 255)
    draw_border(ImageDraw.Draw(base_image), width, height)
    epd.displayPartBaseImage(epd.getbuffer(base_image.rotate(180)))

    # Start button monitoring thread
    threading.Thread(target=button_listener, args=(button, epd), daemon=True).start()

    last_state = None
    while True:
        now = datetime.now()
        if DAY_START_HOUR <= now.hour < DAY_END_HOUR:
            if last_state == "night":
                # After a night-mode full display() call, the partial-refresh base
                # image is stale (goodnight screen). Reset it before resuming clock.
                logging.info("Entering day mode — resetting partial refresh base image.")
                reset_base_image(epd)
            elif last_state != "day":
                logging.info("Entering day mode.")
            try:
                draw_clock(epd)
            except Exception:
                logging.exception("draw_clock() failed in main loop")
            last_state = "day"
        else:
            if last_state != "night":
                logging.info("Entering night mode.")
                display_goodnight(epd)
            last_state = "night"

        time.sleep(UPDATE_INTERVAL)


if __name__ == "__main__":
    main()
