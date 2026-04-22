import logging
import signal
import sys
import time
import threading
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from gpiozero import Button
from subprocess import run
from waveshare_epd import epd2in13_V4

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

# === CONFIGURATION ===
GPIO_PIN = 3
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
UPDATE_INTERVAL = 300  # seconds (5 minutes)

# === FONTS ===
font_large = ImageFont.truetype(FONT_PATH, 28)
font_small = ImageFont.truetype(FONT_PATH, 22)
font_tiny  = ImageFont.truetype(FONT_PATH, 14)

# === EPD LOCK — protects all SPI writes to the display ===
epd_lock = threading.Lock()

# === TIME DESCRIPTIONS ===
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
    font = ImageFont.truetype(FONT_PATH, 24)
    text_bbox = draw.textbbox((0, 0), text, font=font)
    x = (width - (text_bbox[2] - text_bbox[0])) // 2
    y = (height - (text_bbox[3] - text_bbox[1])) // 2

    draw.rounded_rectangle(
        (10, 10, width - 10, height - 10),
        radius=15,
        outline=0,
        width=2
    )
    draw.text((x, y), text, font=font, fill=0)

    with epd_lock:
        epd.display(epd.getbuffer(image.rotate(180)))
    time.sleep(2)

def draw_border(draw, width, height, margin=4):
    r = 6
    draw.rectangle((margin, margin, width - margin, height - margin), outline=0, width=1)
    draw.ellipse((margin + 2, margin + 2, margin + 2 + r, margin + 2 + r), outline=0)
    draw.ellipse((width - margin - r - 2, margin + 2, width - margin - 2, margin + 2 + r), outline=0)
    draw.rectangle((margin + 2, height - margin - r - 2, margin + 2 + r, height - margin - 2), outline=0)
    draw.rectangle((width - margin - r - 2, height - margin - r - 2, width - margin - 2, height - margin - 2), outline=0)

def draw_clock(epd):
    width, height = epd.height, epd.width
    now = datetime.now()

    image = Image.new('1', (width, height), 255)
    draw = ImageDraw.Draw(image)

    phrase, hour_str = fuzzy_time(now.hour, now.minute)
    day_line = now.strftime("%A, %b %d")

    phrase_font = font_small if len(phrase) > 12 else font_large
    phrase_bbox = draw.textbbox((0, 0), phrase, font=phrase_font)
    hour_bbox   = draw.textbbox((0, 0), hour_str, font=font_large)
    day_bbox    = draw.textbbox((0, 0), day_line, font=font_tiny)

    total_height = (
        (phrase_bbox[3] - phrase_bbox[1]) +
        (hour_bbox[3] - hour_bbox[1]) +
        (day_bbox[3] - day_bbox[1]) + 10
    )
    y = (height - total_height) // 2

    draw_border(draw, width, height)
    draw.text(((width - (phrase_bbox[2] - phrase_bbox[0])) // 2, y), phrase, font=phrase_font, fill=0)
    draw.text(((width - (hour_bbox[2] - hour_bbox[0])) // 2, y + (phrase_bbox[3] - phrase_bbox[1]) + 4), hour_str, font=font_large, fill=0)
    draw.text(((width - (day_bbox[2] - day_bbox[0])) // 2, height - day_bbox[3] - 6), day_line, font=font_tiny, fill=0)

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

        if duration >= 5.0:
            shutdown_procedure(epd)
        elif 0.05 < duration < 2.0:
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
        # Day mode: 7:00am–10:59pm (hours 7–22 inclusive)
        if 7 <= now.hour < 23:
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
