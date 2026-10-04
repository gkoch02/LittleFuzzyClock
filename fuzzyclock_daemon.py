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

from fuzzyclock.frames import _CONTENT_PAD
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

# Hardware-only deps, guarded so CI and dev boxes can import this module.
# The except is deliberately broad: importing waveshare_epd claims the GPIO
# pins, and with them already held it raises lgpio.error("GPIO busy"), which is
# neither ImportError nor RuntimeError. Breadth hides the cause, so it is kept
# and reported by main() (in the SystemExit and the button-init log).
_EPD_IMPORT_ERROR = None
_BUTTON_IMPORT_ERROR = None

try:
    from gpiozero import Button
except Exception as exc:
    _BUTTON_IMPORT_ERROR = exc
    Button = None

try:
    from waveshare_epd import epd2in13_V4
except Exception as exc:
    _EPD_IMPORT_ERROR = exc
    epd2in13_V4 = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

# === CONFIGURATION ===
GPIO_PIN = 3
UPDATE_MINUTES = 5  # re-render on wall-clock multiples of this many minutes
TICK_INTERVAL = 60  # main loop wakes every minute to check mode transitions

# Render-failure thresholds. After RENDER_RETRY_REINIT consecutive failures
# we re-init the EPD and force a base-image reseed; after RENDER_RETRY_FATAL
# we exit and let systemd restart us cleanly (RestartSec=10 in the unit file).
RENDER_RETRY_REINIT = 3
RENDER_RETRY_FATAL = 10

# Bound on any single EPD driver call; see _call_with_timeout.
EPD_CALL_TIMEOUT_SEC = 10

# Day mode runs from DAY_START_HOUR up to (but not including) DAY_END_HOUR.
DAY_START_HOUR = 7
DAY_END_HOUR = 23

# Button press classification (seconds).
LONG_PRESS_SECONDS = 5.0  # hold this long → shutdown
SHORT_PRESS_MIN_SECONDS = 0.05  # anything shorter is debounce noise
SHORT_PRESS_MAX_SECONDS = 2.0  # anything between MAX and LONG_PRESS is ignored

# The goodnight slide always uses this blackletter face, whatever FONT_VARIANT is.
GOODNIGHT_FONT = "unifraktur-maguntia"


CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fuzzyclock_config.yaml")


def _load_config(path=CONFIG_PATH):
    """Read the YAML config and return (dialect, font, frame, latitude, longitude).

    Unknown dialect, font, or frame logs a warning and falls back to the
    default; missing or invalid coordinates log a warning and return
    (None, None) so the daemon stays on plain day/night instead of crashing.
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
        latitude, longitude = float(lat_raw), float(lon_raw)
    except (TypeError, ValueError) as exc:
        logging.warning(
            "Config file %s has invalid latitude/longitude (%s); after-hours mode disabled.",
            path,
            exc,
        )
        return dialect, font, frame, None, None

    # NaN/inf would crash sun_times() on every startup; out-of-range values
    # don't crash but silently give wrong sunrise/sunset. Both fail these
    # comparisons (NaN compares false), so one check covers both.
    if not (-90.0 <= latitude <= 90.0) or not (-180.0 <= longitude <= 180.0):
        logging.warning(
            "Config file %s has out-of-range latitude/longitude (%r, %r); "
            "after-hours mode disabled.",
            path,
            lat_raw,
            lon_raw,
        )
        return dialect, font, frame, None, None

    return dialect, font, frame, latitude, longitude


# Daemon config, populated in main() (not at import time) so tests can import
# this module without filesystem reads or warnings.
DIALECT = DEFAULT_DIALECT
FONT_VARIANT = DEFAULT_FONT
FRAME_VARIANT = AUTO_FRAME
LATITUDE = None
LONGITUDE = None
AFTER_HOURS_ENABLED = False

# === FONTS ===
# Set by _init_fonts() once the fonts the render paths need have loaded.
# Not done at import time: load_font() raises SystemExit when a font is missing.
_fonts_ready = False

# Random-font mode state. `_current_random_font` is the variant in use right
# now; `_last_phrase` is the phrase from the most recent successful render so
# we can detect a phrase change and roll a fresh font. Both are touched from
# the main loop and the button thread, hence the lock.
_current_random_font = None
_last_phrase = None
_random_font_lock = threading.Lock()


def _init_fonts():
    """Fail fast at startup if a font the render paths need is missing.

    Loads the goodnight font and, unless in random mode (whose candidates are
    pre-filtered to files on disk), the configured clock font.
    """
    global _fonts_ready
    load_font(24, variant=GOODNIGHT_FONT)
    if FONT_VARIANT != RANDOM_FONT:
        load_font(24, variant=FONT_VARIANT)
    _fonts_ready = True


# The frame last painted onto the partial-refresh base image. In random-font +
# auto-frame mode the frame can change between renders; draw_clock reseeds the
# base when it does, or displayPartial would diff against the old frame and
# leave ghost border pixels.
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

    main() calls this without a phrase to pick the startup base-image frame;
    the first phrased call must reuse that pick rather than re-roll, or the
    frame would mismatch and a shuffle-bag slot would go unseen.
    `_last_phrase is None` marks "no phrase displayed yet".
    """
    global _current_random_font, _last_phrase
    if FONT_VARIANT != RANDOM_FONT:
        return FONT_VARIANT
    with _random_font_lock:
        if _current_random_font is None:
            _current_random_font = pick_random_font()
        elif phrase is not None and _last_phrase is not None and phrase != _last_phrase:
            _current_random_font = pick_random_font()
        if phrase is not None:
            _last_phrase = phrase
        return _current_random_font


def _require_fonts():
    """Fail loudly if a render path runs before _init_fonts()."""
    assert _fonts_ready, "_init_fonts() must run before any render path"


# === EPD LOCK — protects all SPI writes to the display ===
epd_lock = threading.Lock()


class EPDTimeoutError(RuntimeError):
    """A blocking EPD driver call exceeded EPD_CALL_TIMEOUT_SEC.

    Raised by `_call_with_timeout` when the call itself overruns (typically a
    stuck BUSY pin) or when acquiring the lock does (a previous call is still
    wedged). A RuntimeError so the existing render-failure handlers catch it.
    """


def _call_with_timeout(func, *args, timeout=EPD_CALL_TIMEOUT_SEC, lock=None, **kwargs):
    """Run `func(*args, **kwargs)` on a worker thread, bounded by `timeout`.

    The vendored driver's ReadBusy() polls the BUSY pin with no timeout, so a
    stuck pin would hang the caller forever. A worker thread rather than
    SIGALRM because the button thread also calls into the driver, and signals
    only interrupt the main thread.

    A timed-out worker can't be killed and keeps running against the bus. So
    `lock` is acquired here (bounded by `timeout`) and released by the
    *worker* when the call really returns: a later call, e.g. the recovery
    re-init, then times out on the lock instead of driving SPI concurrently.
    Repeated timeouts reach RENDER_RETRY_FATAL, and the process exit is what
    finally sheds the wedged worker.
    """
    if lock is not None and not lock.acquire(timeout=timeout):
        raise EPDTimeoutError(
            f"timed out waiting {timeout}s for epd_lock (a previous call "
            "may still be wedged against the driver)"
        )
    outcome = {}

    def _run():
        try:
            outcome["value"] = func(*args, **kwargs)
        except BaseException as exc:  # re-raised on the caller's thread below
            outcome["error"] = exc
        finally:
            if lock is not None:
                lock.release()

    worker = threading.Thread(target=_run, daemon=True)
    worker.start()
    worker.join(timeout)
    if worker.is_alive():
        name = getattr(func, "__name__", repr(func))
        raise EPDTimeoutError(
            f"{name}() did not return within {timeout}s (EPD BUSY pin likely stuck)"
        )
    if "error" in outcome:
        raise outcome["error"]
    return outcome.get("value")


def _epd_init(epd):
    """Timeout- and lock-guarded `epd.init()`.

    Callers must treat a -1 return as failure: the driver returns it when
    module_init() fails and otherwise carries on against an unconfigured panel.
    """
    return _call_with_timeout(epd.init, lock=epd_lock)


# Serializes draw_clock's check-reseed-render sequence across the main loop and
# the button thread, so one render never diffs against a base painted by the
# other. Reentrant because draw_clock calls reset_base_image while holding it.
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


# current_mode() runs every TICK_INTERVAL but the ephemeris only changes daily.
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
    """
    global _last_applied_frame
    with _render_lock:
        if frame is None:
            frame = _resolve_frame(FONT_VARIANT)
        bg = 0 if invert else 255
        base = Image.new("1", (epd.height, epd.width), bg)
        draw_border(ImageDraw.Draw(base), epd.height, epd.width, invert=invert, frame=frame)
        _call_with_timeout(epd.displayPartBaseImage, epd.getbuffer(base.rotate(180)), lock=epd_lock)
        _last_applied_frame = frame


def display_goodnight(epd):
    """Render the night-mode 'Goodnight' slide.

    Visually mirrors the inverted (after-hours) clock face — black canvas
    with the rustic border in white — but replaces the fuzzy phrase + hour
    with a single auto-sized 'Goodnight' line centered in the canvas, and
    hides the date footer.
    """
    _require_fonts()
    width, height = epd.height, epd.width
    image = Image.new("1", (width, height), 0)
    draw = ImageDraw.Draw(image)

    pad = _CONTENT_PAD  # clears the rustic frame's corner ink
    available_w = width - 2 * pad
    available_h = height - 2 * pad

    text = "Goodnight"
    # Single-line auto-fit: shrink from a higher ceiling than render_clock's
    # 40-pt body cap because we don't have a second line competing for
    # vertical space.
    font = None
    bbox = None
    for size in range(60, 13, -1):
        candidate = load_font(size, variant=GOODNIGHT_FONT)
        cb = draw.textbbox((0, 0), text, font=candidate)
        if (cb[2] - cb[0]) <= available_w and (cb[3] - cb[1]) <= available_h:
            font, bbox = candidate, cb
            break
    if font is None:
        font = load_font(14, variant=GOODNIGHT_FONT)
        bbox = draw.textbbox((0, 0), text, font=font)

    draw_border(draw, width, height, invert=True, frame="rustic")

    text_w = bbox[2] - bbox[0]
    text_ink_h = bbox[3] - bbox[1]
    x = (width - text_w) // 2 - bbox[0]
    y = (height - text_ink_h) // 2 - bbox[1]
    draw.text((x, y), text, font=font, fill=255)

    _call_with_timeout(epd.display, epd.getbuffer(image.rotate(180)), lock=epd_lock)
    time.sleep(2)


def draw_clock(epd, invert=False):
    _require_fonts()
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

        _call_with_timeout(epd.displayPartial, epd.getbuffer(image.rotate(180)), lock=epd_lock)


def shutdown_procedure(epd):
    """Long-press handler: try to leave the panel in a tidy state, then halt.

    Each step is independently guarded so that a transient SPI hiccup on the
    goodnight screen or epd.sleep() doesn't prevent the actual `shutdown -h`
    call — the user pressed-and-held for five seconds, they want a shutdown.

    The unit file runs the daemon as a regular user, so a bare `shutdown`
    would be denied by polkit; `sudo -n` relies on the NOPASSWD rule that
    deploy.sh installs at /etc/sudoers.d/fuzzyclock.
    """
    logging.info("Button long press detected — shutting down.")
    try:
        display_goodnight(epd)
    except Exception:
        logging.exception("display_goodnight() failed during shutdown; continuing.")
    try:
        _call_with_timeout(epd.sleep, lock=epd_lock)
    except Exception:
        logging.exception("epd.sleep() failed during shutdown; continuing.")
    result = run(["sudo", "-n", "shutdown", "-h", "now"])
    if result.returncode != 0:
        logging.error(
            "shutdown command failed (exit %d). The daemon user needs the "
            "sudoers rule deploy.sh installs at /etc/sudoers.d/fuzzyclock.",
            result.returncode,
        )


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
            mode = _current_mode_now()
            if mode == "night":
                # The panel is deep-asleep behind the goodnight slide. A render
                # here would write to a sleeping controller and, even if it
                # succeeded, leave a frozen clock face up until morning — the
                # main loop never repaints goodnight while the mode stays
                # "night".
                logging.info("Short press ignored during night mode.")
                continue
            logging.info("Short press — forcing update.")
            try:
                draw_clock(epd, invert=mode == "after_hours")
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
            "waveshare_epd is unavailable; the fuzzy-clock daemon requires the EPD "
            f"driver. Cause: {_EPD_IMPORT_ERROR!r}. If the pins are busy, another "
            "process already owns them. Use fuzzyclock_preview.py --dry-run for "
            "hardware-free testing."
        )

    global DIALECT, FONT_VARIANT, FRAME_VARIANT, LATITUDE, LONGITUDE, AFTER_HOURS_ENABLED
    DIALECT, FONT_VARIANT, FRAME_VARIANT, LATITUDE, LONGITUDE = _load_config()
    AFTER_HOURS_ENABLED = LATITUDE is not None and LONGITUDE is not None
    _init_fonts()

    epd = epd2in13_V4.EPD()
    if _epd_init(epd) == -1:
        raise SystemExit(
            "epd.init() failed (returned -1); check the panel's SPI/GPIO wiring and power."
        )

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
        # If the gpiozero import itself failed, Button is None and the traceback
        # below is only a TypeError — name the import failure that caused it.
        if _BUTTON_IMPORT_ERROR is not None:
            logging.error("gpiozero import failed: %r", _BUTTON_IMPORT_ERROR)
        logging.exception("Failed to initialise GPIO button; continuing without it.")

    # Seed the partial-refresh base image to match whichever mode we're starting in.
    initial_mode = _current_mode_now()
    reset_base_image(
        epd,
        invert=(initial_mode == "after_hours"),
        frame=_resolve_frame(_resolve_font()),
    )

    last_state = None
    # True while the panel is in deep sleep behind the goodnight slide. The
    # controller must be re-inited before the next SPI write; the button
    # thread can't race this because it ignores short presses in night mode.
    panel_asleep = False

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
                    # Deep-sleep the controller until morning — the goodnight
                    # image persists on the e-ink without power, and Waveshare
                    # advises against leaving the panel driven for hours with
                    # no refresh. Skipped if goodnight failed: the panel state
                    # is unknown and the morning render path can recover it.
                    try:
                        _call_with_timeout(epd.sleep, lock=epd_lock)
                        panel_asleep = True
                    except Exception:
                        logging.exception("epd.sleep() failed entering night mode")
        else:
            invert = mode == "after_hours"
            # Any transition into a clock-displaying mode (or a swap between
            # normal/inverted) leaves the partial-refresh base image stale, so
            # we re-seed it before the next displayPartial call. The very
            # first iteration is already covered by the seed above.
            if last_state is not None and last_state != mode:
                logging.info("Entering %s mode.", mode.replace("_", "-"))
                try:
                    if panel_asleep:
                        # Waking from the overnight deep sleep: the controller
                        # needs a full re-init before any SPI write.
                        if _epd_init(epd) == -1:
                            raise RuntimeError(
                                "epd.init() failed (returned -1) while waking the panel"
                            )
                        panel_asleep = False
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
            should_render = last_state != mode or datetime.now().minute % UPDATE_MINUTES == 0
            if should_render:
                try:
                    if _needs_recovery:
                        if _epd_init(epd) == -1:
                            raise RuntimeError(
                                "epd.init() failed (returned -1) during recovery re-init"
                            )
                        # A full init also wakes a slept controller, e.g. when
                        # the morning wake-up init itself failed and recovery
                        # is what actually brought the panel back.
                        panel_asleep = False
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
    # Skipped if the overnight sleep already ran — epd.sleep() tears down the
    # SPI handle, so a second call would just raise.
    if panel_asleep:
        logging.info("Main loop exited; panel already asleep.")
    else:
        logging.info("Main loop exited; sleeping display.")
        try:
            _call_with_timeout(epd.sleep, lock=epd_lock)
        except Exception:
            logging.exception("epd.sleep() failed during shutdown")


if __name__ == "__main__":
    main()
