import logging
import os
import signal
import threading
import time
from datetime import datetime, timezone
from functools import lru_cache
from subprocess import run

import yaml
from PIL import Image, ImageDraw

from fuzzyclock_core import (
    AUTO_FRAME,
    DEFAULT_DIALECT,
    DEFAULT_FONT,
    DIALECTS,
    FONT_VARIANTS,
    FRAME_VARIANTS,
    RANDOM_FONT,
    draw_border,
    frame_for_font,
    fuzzy_time,
    load_font,
    pick_random_font,
    render_clock,
)
from fuzzyclock_core import sun_times as _raw_sun_times

# Hardware-only deps. Guarded so the module is importable on CI / dev boxes
# without GPIO + an EPD driver installed; the daemon's main() will refuse to
# run if they're missing, but tests can import this file freely. RuntimeError
# is raised by gpiozero on non-Pi Linux when it can't find a GPIO backend.
try:
    from gpiozero import Button
except (ImportError, RuntimeError):
    Button = None

try:
    from waveshare_epd import epd2in13_V4
except (ImportError, RuntimeError):
    epd2in13_V4 = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

# === CONFIGURATION ===
GPIO_PIN = 3
UPDATE_INTERVAL = 300  # render the clock face every 5 minutes
TICK_INTERVAL = 60  # main loop wakes every minute to check mode transitions

# Render-failure thresholds. After RENDER_RETRY_REINIT consecutive failures
# we re-init the EPD and force a base-image reseed; after RENDER_RETRY_FATAL
# we exit and let systemd restart us cleanly (RestartSec=10 in the unit file).
RENDER_RETRY_REINIT = 3
RENDER_RETRY_FATAL = 10

# Day mode runs from DAY_START_HOUR up to (but not including) DAY_END_HOUR.
DAY_START_HOUR = 7
DAY_END_HOUR = 23

# Button press classification (seconds).
LONG_PRESS_SECONDS = 5.0  # hold this long → shutdown
SHORT_PRESS_MIN_SECONDS = 0.05  # anything shorter is debounce noise
SHORT_PRESS_MAX_SECONDS = 2.0  # anything between MAX and LONG_PRESS is ignored


CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fuzzyclock_config.yaml")


def _load_config(path=CONFIG_PATH):
    """Read the YAML config and return (dialect, font, frame, latitude, longitude).

    Validation matches the previous JSON+env-var behaviour: unknown dialect,
    font, or frame logs a warning and falls back to the default; missing or
    invalid coordinates log a warning and return (None, None) so the daemon
    stays on plain day/night instead of crashing.
    """
    try:
        with open(path) as f:
            cfg = yaml.safe_load(f) or {}
    except FileNotFoundError:
        logging.warning(
            "Config file %s not found; using defaults and after-hours mode disabled.",
            path,
        )
        return DEFAULT_DIALECT, DEFAULT_FONT, AUTO_FRAME, None, None
    except (OSError, yaml.YAMLError) as exc:
        logging.warning(
            "Could not read %s (%s); using defaults and after-hours mode disabled.",
            path,
            exc,
        )
        return DEFAULT_DIALECT, DEFAULT_FONT, AUTO_FRAME, None, None

    if not isinstance(cfg, dict):
        logging.warning(
            "Config file %s is not a YAML mapping; using defaults and after-hours mode disabled.",
            path,
        )
        return DEFAULT_DIALECT, DEFAULT_FONT, AUTO_FRAME, None, None

    dialect = cfg.get("dialect", DEFAULT_DIALECT)
    if dialect not in DIALECTS:
        logging.warning(
            "Unknown dialect=%r in %s; falling back to %r. Valid: %s",
            dialect,
            path,
            DEFAULT_DIALECT,
            sorted(DIALECTS.keys()),
        )
        dialect = DEFAULT_DIALECT

    font = cfg.get("font", DEFAULT_FONT)
    if font != RANDOM_FONT and font not in FONT_VARIANTS:
        logging.warning(
            "Unknown font=%r in %s; falling back to %r. Valid: %s",
            font,
            path,
            DEFAULT_FONT,
            sorted([RANDOM_FONT, *FONT_VARIANTS.keys()]),
        )
        font = DEFAULT_FONT

    frame = cfg.get("frame", AUTO_FRAME)
    if frame != AUTO_FRAME and frame not in FRAME_VARIANTS:
        logging.warning(
            "Unknown frame=%r in %s; falling back to %r. Valid: %s",
            frame,
            path,
            AUTO_FRAME,
            sorted([AUTO_FRAME, *FRAME_VARIANTS.keys()]),
        )
        frame = AUTO_FRAME

    lat_raw = cfg.get("latitude")
    lon_raw = cfg.get("longitude")
    if lat_raw is None and lon_raw is None:
        return dialect, font, frame, None, None
    try:
        return dialect, font, frame, float(lat_raw), float(lon_raw)
    except (TypeError, ValueError) as exc:
        logging.warning(
            "Config file %s has invalid latitude/longitude (%s); after-hours mode disabled.",
            path,
            exc,
        )
        return dialect, font, frame, None, None


# Daemon config. These are populated in main() rather than at import time so
# that test code can `import fuzzyclock_daemon` without triggering a config
# read or warning logs. _current_mode_now() and draw_clock() read them, but
# they're only ever called from inside main()'s control flow.
DIALECT = DEFAULT_DIALECT
FONT_VARIANT = DEFAULT_FONT
FRAME_VARIANT = AUTO_FRAME
LATITUDE = None
LONGITUDE = None
AFTER_HOURS_ENABLED = False

# === FONTS ===
# Populated by _init_fonts() from main(), not at import time, so test code can
# `import fuzzyclock_daemon` on a host without DejaVu installed (load_font()
# raises SystemExit when no candidate is found). Same rationale as the config
# globals above.
font_goodnight = None

# Random-font mode state. `_current_random_font` is the variant in use right
# now; `_last_phrase` is the phrase from the most recent successful render so
# we can detect a phrase change and roll a fresh font. Both are touched from
# the main loop and the button thread, hence the lock.
_current_random_font = None
_last_phrase = None
_random_font_lock = threading.Lock()


def _init_fonts():
    """Populate the font globals. Must run before any render path is invoked.

    render_clock auto-sizes its body fonts at render time, so only the
    goodnight font needs to be pre-loaded here. In random-font mode we seed
    the current pick here so the goodnight screen has a concrete variant
    available even before the first clock-face render.
    """
    global font_goodnight, _current_random_font
    if FONT_VARIANT == RANDOM_FONT:
        _current_random_font = pick_random_font()
        font_goodnight = load_font(24, variant=_current_random_font)
    else:
        font_goodnight = load_font(24, variant=FONT_VARIANT)


# Tracks the frame name that was last painted onto the partial-refresh base
# image. In random-font + auto-frame mode the variant (and therefore the
# frame) can shift between renders; if draw_clock noticed a frame change
# without re-seeding the base, displayPartial would diff against the old
# frame and leave ghost border pixels. Updated by reset_base_image, consulted
# by draw_clock.
_last_applied_frame = None


def _resolve_frame(font_variant):
    """Concrete frame name for `font_variant` under the active FRAME_VARIANT.

    Mirrors how _resolve_font handles random fonts: an explicit frame in
    config wins; AUTO_FRAME defers to frame_for_font(font_variant), which
    keeps the border in step with whichever font is currently rendering.
    """
    if FRAME_VARIANT == AUTO_FRAME:
        return frame_for_font(font_variant)
    return FRAME_VARIANT


def _resolve_font(phrase=None):
    """Concrete font variant for the next render.

    In random mode, picks a new vendored variant whenever the rendered phrase
    differs from the previous render — so the font changes in lockstep with
    the time phrasing (every 5 minutes, plus on dialect-driven boundaries).
    A button press inside the same phrase keeps the current pick so the user
    sees the "same" clock when they tap for a refresh. Returns FONT_VARIANT
    verbatim when random mode is off.
    """
    global _current_random_font, _last_phrase
    if FONT_VARIANT != RANDOM_FONT:
        return FONT_VARIANT
    with _random_font_lock:
        if _current_random_font is None or (phrase is not None and phrase != _last_phrase):
            _current_random_font = pick_random_font()
        if phrase is not None:
            _last_phrase = phrase
        return _current_random_font


def _require_fonts():
    """Fail loudly if a render path runs before _init_fonts().

    PIL's draw.text() silently falls back to a default bitmap font when handed
    None, which would render a subtly-wrong clock face instead of crashing —
    much harder to debug than a clear AssertionError. This guard keeps the
    failure mode loud, matching the pre-refactor behaviour where load_font()
    raised SystemExit at import.
    """
    assert font_goodnight is not None, "_init_fonts() must run before any render path"


# === EPD LOCK — protects all SPI writes to the display ===
epd_lock = threading.Lock()

# Render lock — serializes the check-then-reseed sequence on _last_applied_frame
# and the surrounding render/displayPartial so the main loop and the button
# thread can't interleave a frame change with another thread's render. Without
# it, two concurrent draw_clock calls could pick different frames, both reseed
# the partial-refresh base, and leave one render diffing against a base painted
# by the other call. Reentrant so reset_base_image can be invoked from inside
# draw_clock without deadlocking.
_render_lock = threading.RLock()

# Set by the SIGTERM/SIGINT handler so the main loop and the button-thread
# supervisor can break out of their waits and exit cleanly. Routing shutdown
# through an Event (instead of acquiring epd_lock inside the signal handler)
# avoids a deadlock if a signal arrives mid-render.
_stop_event = threading.Event()

# Render-failure state. The button thread and the main loop both call
# draw_clock; we track failures across both so the recovery + fatal-exit
# thresholds reflect actual panel health, not just main-loop activity.
_render_state_lock = threading.Lock()
_consecutive_failures = 0
_needs_recovery = False


def _on_render_success():
    """Called after any successful SPI write; clears the recovery flags."""
    global _consecutive_failures, _needs_recovery
    with _render_state_lock:
        _consecutive_failures = 0
        _needs_recovery = False


def _on_render_failure():
    """Called after a draw failure. Returns (count, fatal); also flips the
    recovery flag once we've crossed RENDER_RETRY_REINIT."""
    global _consecutive_failures, _needs_recovery
    with _render_state_lock:
        _consecutive_failures += 1
        if _consecutive_failures >= RENDER_RETRY_REINIT:
            _needs_recovery = True
        return _consecutive_failures, _consecutive_failures >= RENDER_RETRY_FATAL


def _sleep_to_next_tick(interval, now=None):
    """Return seconds until the next wall-clock multiple of `interval`.

    The result is always in (0, interval]. Sleeping for this duration keeps
    the daemon's ticks aligned with wall-clock minutes regardless of how
    long the previous render took, which eliminates cumulative drift.
    """
    now = now if now is not None else time.time()
    delay = interval - (now % interval)
    return delay if delay > 0 else interval


# The ephemeris is stable for a calendar day, but current_mode() is now
# evaluated every TICK_INTERVAL (60s). maxsize=4 covers today, yesterday at
# midnight rollover, and a small buffer; older entries self-evict.
@lru_cache(maxsize=4)
def _sun_times_cached(date, latitude, longitude):
    return _raw_sun_times(date, latitude, longitude)


def current_mode(
    now, latitude, longitude, after_hours_enabled, day_start=DAY_START_HOUR, day_end=DAY_END_HOUR
):
    """Return one of "day", "after_hours", "night" for the given local time.

    Outside the wake window we're always in night/goodnight. Inside it, the sun
    decides between day (normal ink) and after-hours (inverted ink). When
    `after_hours_enabled` is False (no coordinates configured), or for polar
    night / midnight sun where the sun never crosses the horizon, we fall
    back to plain day inside the wake window.
    """
    if not (day_start <= now.hour < day_end):
        return "night"
    if not after_hours_enabled:
        return "day"
    sunrise, sunset = _sun_times_cached(now.date(), latitude, longitude)
    if sunrise is None or sunset is None:
        return "day"
    now_utc = now.astimezone(timezone.utc)
    return "day" if sunrise <= now_utc <= sunset else "after_hours"


def _current_mode_now():
    """`current_mode` evaluated against the module-level config and wall clock."""
    return current_mode(
        datetime.now().astimezone(),
        LATITUDE,
        LONGITUDE,
        AFTER_HOURS_ENABLED,
    )


def reset_base_image(epd, invert=False, frame=None):
    """Re-issue a blank base image for partial refresh.

    Required after any full epd.display() call (e.g. the goodnight screen) and
    whenever the foreground/background swap, since partial refresh diffs
    against the previously-set base image. `frame` selects which border style
    is painted onto the base; defaults to the resolved frame for the current
    fixed font (random-font callers pass an explicit frame so the base matches
    the variant they're about to render with).

    Held under _render_lock so the base-image swap and the corresponding
    update to _last_applied_frame can't interleave with a concurrent
    draw_clock call from the button thread.
    """
    global _last_applied_frame
    with _render_lock:
        if frame is None:
            frame = _resolve_frame(FONT_VARIANT)
        bg = 0 if invert else 255
        with epd_lock:
            base = Image.new("1", (epd.height, epd.width), bg)
            draw_border(ImageDraw.Draw(base), epd.height, epd.width, invert=invert, frame=frame)
            epd.displayPartBaseImage(epd.getbuffer(base.rotate(180)))
        _last_applied_frame = frame


def display_goodnight(epd):
    _require_fonts()
    width, height = epd.height, epd.width
    image = Image.new("1", (width, height), 255)
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
    _require_fonts()

    # Held for the entire body so the main loop and the button thread can't
    # interleave the _last_applied_frame check with another thread's reseed —
    # an interleave would let one render diff against a base painted by the
    # other call and ghost the previous border. Reentrant so the nested
    # reset_base_image call below doesn't deadlock.
    with _render_lock:
        width, height = epd.height, epd.width
        bg = 0 if invert else 255
        image = Image.new("1", (width, height), bg)
        draw = ImageDraw.Draw(image)

        now = datetime.now()
        # Resolve the font before render so random-mode picks a fresh variant
        # whenever the phrase rolls over to the next 5-minute bucket.
        phrase, _ = fuzzy_time(now.hour, now.minute, DIALECT)
        variant = _resolve_font(phrase)
        frame = _resolve_frame(variant)

        # Random-font + auto-frame mode can pick a font in a new category
        # between ticks; without re-seeding the partial-refresh base,
        # displayPartial would diff against the old frame and ghost it.
        if frame != _last_applied_frame:
            reset_base_image(epd, invert=invert, frame=frame)

        render_clock(
            draw,
            width,
            height,
            now,
            font_variant=variant,
            dialect=DIALECT,
            invert=invert,
            frame=frame,
        )

        with epd_lock:
            epd.displayPartial(epd.getbuffer(image.rotate(180)))


def shutdown_procedure(epd):
    """Long-press handler: try to leave the panel in a tidy state, then halt.

    Each step is independently guarded so that a transient SPI hiccup on the
    goodnight screen or epd.sleep() doesn't prevent the actual `shutdown -h`
    call — the user pressed-and-held for five seconds, they want a shutdown.
    """
    logging.info("Button long press detected — shutting down.")
    try:
        display_goodnight(epd)
    except Exception:
        logging.exception("display_goodnight() failed during shutdown; continuing.")
    try:
        with epd_lock:
            epd.sleep()
    except Exception:
        logging.exception("epd.sleep() failed during shutdown; continuing.")
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
                draw_clock(epd, invert=_current_mode_now() == "after_hours")
                _on_render_success()
            except Exception:
                count, fatal = _on_render_failure()
                logging.exception(
                    "draw_clock() failed on button press (%d/%d).",
                    count,
                    RENDER_RETRY_FATAL,
                )
                # Recovery itself happens in the main loop's render path,
                # but if we've crossed the fatal threshold here we signal
                # main to exit so systemd can restart us with a clean slate.
                if fatal:
                    _stop_event.set()
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
    if epd2in13_V4 is None:
        raise SystemExit(
            "waveshare_epd is not installed; the fuzzy-clock daemon requires the "
            "EPD driver. Use fuzzyClock2.py --dry-run for hardware-free testing."
        )

    # Load configuration here rather than at import time so tests can import
    # the module without triggering warnings or filesystem reads. After-hours
    # mode is location-driven via fuzzyclock_config.yaml next to this file;
    # if it's missing or malformed, the feature stays off and we fall back
    # to plain day/night.
    global DIALECT, FONT_VARIANT, FRAME_VARIANT, LATITUDE, LONGITUDE, AFTER_HOURS_ENABLED
    DIALECT, FONT_VARIANT, FRAME_VARIANT, LATITUDE, LONGITUDE = _load_config()
    AFTER_HOURS_ENABLED = LATITUDE is not None and LONGITUDE is not None
    _init_fonts()

    epd = epd2in13_V4.EPD()
    epd.init()

    if AFTER_HOURS_ENABLED:
        logging.info(
            "After-hours mode enabled at lat=%.4f lon=%.4f.",
            LATITUDE,
            LONGITUDE,
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
            target=_button_supervisor,
            args=(button, epd),
            daemon=True,
        ).start()
    except Exception:
        logging.exception("Failed to initialise GPIO button; continuing without it.")

    # Seed the partial-refresh base image to match whichever mode we're starting in.
    initial_mode = _current_mode_now()
    reset_base_image(
        epd,
        invert=(initial_mode == "after_hours"),
        frame=_resolve_frame(_resolve_font()),
    )

    last_state = None

    while not _stop_event.is_set():
        mode = _current_mode_now()
        if mode == "night":
            if last_state != "night":
                logging.info("Entering night mode.")
                try:
                    display_goodnight(epd)
                    # A successful goodnight is a clean SPI write; treat it
                    # as evidence that the panel is healthy and reset any
                    # stale failure state from earlier in the day.
                    _on_render_success()
                except Exception:
                    # Log and accept stale state until morning. If we crashed
                    # here instead, systemd would restart us and we'd retry
                    # immediately — fine once, but a stuck panel could burn
                    # through StartLimitBurst and disable the unit overnight.
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
                    reset_base_image(
                        epd,
                        invert=invert,
                        frame=_resolve_frame(_resolve_font()),
                    )
                except Exception:
                    logging.exception("reset_base_image() failed; will recover via re-init")
                    _on_render_failure()

            # Render on mode change or on every 5-minute wall-clock boundary.
            # The 60s tick gives us ~1-minute mode-transition latency without
            # actually pushing pixels every minute.
            should_render = last_state != mode or datetime.now().minute % 5 == 0
            if should_render:
                try:
                    if _needs_recovery:
                        with epd_lock:
                            epd.init()
                        reset_base_image(
                            epd,
                            invert=invert,
                            frame=_resolve_frame(_resolve_font()),
                        )
                    draw_clock(epd, invert=invert)
                    _on_render_success()
                except Exception:
                    count, fatal = _on_render_failure()
                    logging.exception(
                        "draw_clock() failed (%d/%d).",
                        count,
                        RENDER_RETRY_FATAL,
                    )
                    if fatal:
                        logging.critical(
                            "draw_clock() failed %d times consecutively; "
                            "exiting for systemd to restart us.",
                            count,
                        )
                        break
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
