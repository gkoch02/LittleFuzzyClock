"""Unit tests for the pure helpers in fuzzyclock_daemon.

Covers `current_mode` (across the day/night/after-hours branch table),
`_sleep_to_next_tick` (boundary math), `_load_config` (YAML config-file
error paths and dialect/font/coordinate validation), the button thread's
press classification and supervisor restart logic, the shutdown procedure's
independent guards, the cross-thread render counter, and the EPD-touching
helpers via a fake panel.

The daemon's hardware imports are guarded (see fuzzyclock_daemon top-of-file),
so this test file imports the module directly without stubbing GPIO/EPD.
"""

import os
import tempfile
import threading
import unittest
from datetime import date, datetime, timezone
from unittest import mock

import yaml

import fuzzyclock_daemon as d


class CurrentModeTests(unittest.TestCase):
    """Pure-function tests after the B1 signature refactor."""

    def setUp(self):
        # The daemon caches sun_times by (date, lat, lon). Clear it between
        # tests so a future patched _raw_sun_times can't be shadowed by an
        # entry left over from a real-math test.
        d._sun_times_cached.cache_clear()

    def _at(self, hour, minute=0, month=4, day=26):
        # 2026-04-26 is the project's notional "today"; specific date only
        # matters when after_hours_enabled is True (sun_times runs).
        return datetime(2026, month, day, hour, minute, tzinfo=timezone.utc)

    def test_before_wake_window_is_night(self):
        self.assertEqual(d.current_mode(self._at(5), None, None, False), "night")
        # Even with coordinates configured, before DAY_START_HOUR is night.
        self.assertEqual(d.current_mode(self._at(6, 59), 51.5, -0.1, True), "night")

    def test_after_wake_window_is_night(self):
        # DAY_END_HOUR is exclusive: hour 23 is night.
        self.assertEqual(d.current_mode(self._at(23), None, None, False), "night")
        self.assertEqual(d.current_mode(self._at(23, 30), 51.5, -0.1, True), "night")

    def test_wake_window_without_coordinates_is_always_day(self):
        for hour in (7, 12, 18, 22):
            with self.subTest(hour=hour):
                self.assertEqual(
                    d.current_mode(self._at(hour), None, None, False),
                    "day",
                )

    def test_after_hours_during_summer_evening_in_london(self):
        # London at June solstice: sunset ~20:21 UTC. 21:00 is past sunset
        # but still inside the 7..23 wake window → after_hours.
        when = datetime(2024, 6, 21, 21, 0, tzinfo=timezone.utc)
        self.assertEqual(d.current_mode(when, 51.5074, -0.1278, True), "after_hours")

    def test_day_during_summer_afternoon_in_london(self):
        # 14:00 UTC, sun is well up → day.
        when = datetime(2024, 6, 21, 14, 0, tzinfo=timezone.utc)
        self.assertEqual(d.current_mode(when, 51.5074, -0.1278, True), "day")

    def test_polar_midnight_sun_falls_back_to_day(self):
        # Tromsø in summer: sun never sets → sun_times returns (None, None)
        # and the function falls back to "day" inside the wake window.
        when = datetime(2024, 6, 21, 12, 0, tzinfo=timezone.utc)
        self.assertEqual(d.current_mode(when, 69.6492, 18.9553, True), "day")

    def test_custom_wake_window_overrides_module_defaults(self):
        # A caller can override day_start/day_end without touching globals.
        when = self._at(6)
        self.assertEqual(
            d.current_mode(when, None, None, False, day_start=5, day_end=22),
            "day",
        )

    def test_exact_sunset_boundary_is_still_day(self):
        # Comparison is inclusive on both ends (sunrise <= now <= sunset).
        # Mock _sun_times_cached so this test doesn't depend on the real
        # ephemeris numbers — we just want to verify the boundary semantics.
        sunrise = datetime(2024, 6, 21, 5, 0, tzinfo=timezone.utc)
        sunset = datetime(2024, 6, 21, 20, 0, tzinfo=timezone.utc)
        with mock.patch.object(d, "_sun_times_cached", return_value=(sunrise, sunset)):
            self.assertEqual(d.current_mode(sunset, 0.0, 0.0, True), "day")
            one_second_later = sunset.replace(second=1)
            self.assertEqual(d.current_mode(one_second_later, 0.0, 0.0, True), "after_hours")


class RenderStateTests(unittest.TestCase):
    """The cross-thread retry counter and recovery flag added during the
    code-review fixes; lets the button thread's failures trigger main-loop
    recovery, and lets goodnight clear stale failure state."""

    def setUp(self):
        # Reset module state between tests so they don't bleed.
        d._on_render_success()

    def tearDown(self):
        d._on_render_success()

    def test_success_clears_counter_and_recovery_flag(self):
        for _ in range(d.RENDER_RETRY_REINIT):
            d._on_render_failure()
        self.assertTrue(d._needs_recovery)
        d._on_render_success()
        self.assertEqual(d._consecutive_failures, 0)
        self.assertFalse(d._needs_recovery)

    def test_recovery_flag_flips_at_reinit_threshold(self):
        for _ in range(d.RENDER_RETRY_REINIT - 1):
            count, fatal = d._on_render_failure()
            self.assertFalse(fatal)
            self.assertFalse(d._needs_recovery)
        count, fatal = d._on_render_failure()
        self.assertEqual(count, d.RENDER_RETRY_REINIT)
        self.assertTrue(d._needs_recovery)
        self.assertFalse(fatal)

    def test_fatal_returned_at_fatal_threshold(self):
        fatal = False
        for _ in range(d.RENDER_RETRY_FATAL):
            _count, fatal = d._on_render_failure()
        self.assertTrue(fatal)


class SleepToNextTickTests(unittest.TestCase):
    """The result is always in (0, interval]; never zero (which would busy-loop)."""

    def test_exact_boundary_returns_full_interval(self):
        self.assertEqual(d._sleep_to_next_tick(60, now=0.0), 60.0)
        self.assertEqual(d._sleep_to_next_tick(60, now=60.0), 60.0)
        self.assertEqual(d._sleep_to_next_tick(300, now=900.0), 300.0)

    def test_mid_bucket_returns_remainder(self):
        self.assertEqual(d._sleep_to_next_tick(60, now=90.0), 30.0)
        self.assertEqual(d._sleep_to_next_tick(300, now=12.5), 287.5)

    def test_just_before_next_boundary(self):
        self.assertAlmostEqual(d._sleep_to_next_tick(60, now=119.5), 0.5)

    def test_default_now_uses_wall_clock(self):
        # Mocking time.time keeps this deterministic.
        with mock.patch("fuzzyclock_daemon.time.time", return_value=42.0):
            self.assertEqual(d._sleep_to_next_tick(60), 18.0)


class LoadConfigTests(unittest.TestCase):
    def _write(self, contents):
        path = os.path.join(self.tmp.name, "fuzzyclock_config.yaml")
        with open(path, "w") as f:
            f.write(contents)
        return path

    def _write_yaml(self, mapping):
        return self._write(yaml.safe_dump(mapping))

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_file_returns_defaults(self):
        missing = os.path.join(self.tmp.name, "does_not_exist.yaml")
        self.assertEqual(
            d._load_config(missing),
            (d.DEFAULT_DIALECT, d.DEFAULT_FONT, d.AUTO_FRAME, None, None),
        )

    def test_malformed_yaml_returns_defaults(self):
        path = self._write("dialect: classic\n  - oops: not valid")
        self.assertEqual(
            d._load_config(path),
            (d.DEFAULT_DIALECT, d.DEFAULT_FONT, d.AUTO_FRAME, None, None),
        )

    def test_empty_file_returns_defaults(self):
        path = self._write("")
        self.assertEqual(
            d._load_config(path),
            (d.DEFAULT_DIALECT, d.DEFAULT_FONT, d.AUTO_FRAME, None, None),
        )

    def test_non_mapping_yaml_returns_defaults(self):
        path = self._write("- not\n- a mapping\n")
        with self.assertLogs("root", level="WARNING"):
            self.assertEqual(
                d._load_config(path),
                (d.DEFAULT_DIALECT, d.DEFAULT_FONT, d.AUTO_FRAME, None, None),
            )

    def test_unknown_dialect_falls_back_with_warning(self):
        path = self._write_yaml({"dialect": "pirate"})
        with self.assertLogs("root", level="WARNING") as cm:
            dialect, font, frame, lat, lon = d._load_config(path)
        self.assertEqual(dialect, d.DEFAULT_DIALECT)
        self.assertEqual(font, d.DEFAULT_FONT)
        self.assertEqual(frame, d.AUTO_FRAME)
        self.assertIsNone(lat)
        self.assertIsNone(lon)
        self.assertTrue(any("pirate" in line for line in cm.output))

    def test_unknown_font_falls_back_with_warning(self):
        path = self._write_yaml({"font": "comic-sans"})
        with self.assertLogs("root", level="WARNING") as cm:
            dialect, font, _frame, _lat, _lon = d._load_config(path)
        self.assertEqual(dialect, d.DEFAULT_DIALECT)
        self.assertEqual(font, d.DEFAULT_FONT)
        self.assertTrue(any("comic-sans" in line for line in cm.output))

    def test_known_dialect_and_font_are_returned(self):
        path = self._write_yaml({"dialect": "shakespeare", "font": "roboto-slab"})
        dialect, font, frame, lat, lon = d._load_config(path)
        self.assertEqual(dialect, "shakespeare")
        self.assertEqual(font, "roboto-slab")
        self.assertEqual(frame, d.AUTO_FRAME)
        self.assertIsNone(lat)
        self.assertIsNone(lon)

    def test_valid_full_config(self):
        path = self._write_yaml(
            {
                "dialect": "shakespeare",
                "font": "roboto-slab",
                "frame": "rustic",
                "latitude": 51.5074,
                "longitude": -0.1278,
            }
        )
        dialect, font, frame, lat, lon = d._load_config(path)
        self.assertEqual(dialect, "shakespeare")
        self.assertEqual(font, "roboto-slab")
        self.assertEqual(frame, "rustic")
        self.assertAlmostEqual(lat, 51.5074)
        self.assertAlmostEqual(lon, -0.1278)

    def test_missing_coords_disables_after_hours(self):
        path = self._write_yaml({"dialect": "classic", "font": "dejavu"})
        _dialect, _font, _frame, lat, lon = d._load_config(path)
        self.assertIsNone(lat)
        self.assertIsNone(lon)

    def test_partial_coords_disables_after_hours_with_warning(self):
        path = self._write_yaml({"latitude": 51.5})  # no longitude
        with self.assertLogs("root", level="WARNING"):
            _dialect, _font, _frame, lat, lon = d._load_config(path)
        self.assertIsNone(lat)
        self.assertIsNone(lon)

    def test_non_numeric_coords_disable_after_hours_with_warning(self):
        path = self._write_yaml({"latitude": "north", "longitude": -0.1})
        with self.assertLogs("root", level="WARNING"):
            _dialect, _font, _frame, lat, lon = d._load_config(path)
        self.assertIsNone(lat)
        self.assertIsNone(lon)

    def test_random_font_value_is_accepted(self):
        # `random` is a valid sentinel even though it isn't a key in
        # FONT_VARIANTS; _load_config must not warn or fall back.
        path = self._write_yaml({"font": "random"})
        with self.assertNoLogs("root", level="WARNING"):
            _dialect, font, _frame, _lat, _lon = d._load_config(path)
        self.assertEqual(font, d.RANDOM_FONT)

    def test_known_frame_is_accepted(self):
        path = self._write_yaml({"frame": "sketchy"})
        with self.assertNoLogs("root", level="WARNING"):
            _dialect, _font, frame, _lat, _lon = d._load_config(path)
        self.assertEqual(frame, "sketchy")

    def test_auto_frame_value_is_accepted(self):
        # `auto` is the sentinel; valid even though it isn't a key in
        # FRAME_VARIANTS. Must not warn or fall back.
        path = self._write_yaml({"frame": "auto"})
        with self.assertNoLogs("root", level="WARNING"):
            _dialect, _font, frame, _lat, _lon = d._load_config(path)
        self.assertEqual(frame, d.AUTO_FRAME)

    def test_unknown_frame_falls_back_with_warning(self):
        path = self._write_yaml({"frame": "art-deco"})
        with self.assertLogs("root", level="WARNING") as cm:
            _dialect, _font, frame, _lat, _lon = d._load_config(path)
        self.assertEqual(frame, d.AUTO_FRAME)
        self.assertTrue(any("art-deco" in line for line in cm.output))

    def test_oserror_other_than_fnf_returns_defaults_with_warning(self):
        # The (OSError, yaml.YAMLError) branch is separate from the
        # FileNotFoundError branch. A PermissionError (or any other OSError
        # subclass that isn't FileNotFoundError) must also fall back to
        # defaults and emit a warning.
        path = os.path.join(self.tmp.name, "unreadable.yaml")
        with mock.patch("builtins.open", side_effect=PermissionError("access denied")):
            with self.assertLogs("root", level="WARNING") as cm:
                result = d._load_config(path)
        self.assertEqual(result, (d.DEFAULT_DIALECT, d.DEFAULT_FONT, d.AUTO_FRAME, None, None))
        self.assertTrue(any("access denied" in line for line in cm.output))


class ResolveFontTests(unittest.TestCase):
    """`_resolve_font` is the daemon's hook for random-font mode: it returns
    the configured variant verbatim except in random mode, where it picks a
    fresh variant whenever the rendered phrase changes."""

    def setUp(self):
        # Save and reset the module's random-font state so tests don't bleed.
        self._saved_variant = d.FONT_VARIANT
        self._saved_current = d._current_random_font
        self._saved_phrase = d._last_phrase
        d._current_random_font = None
        d._last_phrase = None

    def tearDown(self):
        d.FONT_VARIANT = self._saved_variant
        d._current_random_font = self._saved_current
        d._last_phrase = self._saved_phrase

    def test_non_random_returns_configured_variant(self):
        d.FONT_VARIANT = "roboto-slab"
        self.assertEqual(d._resolve_font("anything"), "roboto-slab")
        self.assertEqual(d._resolve_font(None), "roboto-slab")

    def test_random_seeds_initial_pick(self):
        # First call with no prior state should pick a real variant.
        d.FONT_VARIANT = d.RANDOM_FONT
        with mock.patch.object(d, "pick_random_font", return_value="ubuntu") as pick:
            picked = d._resolve_font("half past")
        self.assertEqual(picked, "ubuntu")
        pick.assert_called_once()

    def test_random_keeps_pick_within_same_phrase(self):
        # Multiple resolves within the same phrase must NOT re-pick — that
        # would change the font on every button-press refresh.
        d.FONT_VARIANT = d.RANDOM_FONT
        sequence = iter(["ubuntu", "fredoka", "playfair"])
        with mock.patch.object(d, "pick_random_font", side_effect=lambda: next(sequence)):
            first = d._resolve_font("half past")
            second = d._resolve_font("half past")
            third = d._resolve_font("half past")
        self.assertEqual(first, "ubuntu")
        self.assertEqual(second, "ubuntu")
        self.assertEqual(third, "ubuntu")

    def test_random_re_picks_on_phrase_change(self):
        d.FONT_VARIANT = d.RANDOM_FONT
        sequence = iter(["ubuntu", "fredoka"])
        with mock.patch.object(d, "pick_random_font", side_effect=lambda: next(sequence)):
            first = d._resolve_font("half past")
            second = d._resolve_font("twenty to")
        self.assertEqual(first, "ubuntu")
        self.assertEqual(second, "fredoka")

    def test_random_with_phrase_none_keeps_current_pick(self):
        # phrase=None means "I don't know what's on screen" — used by code
        # paths that just want the currently-active variant. Must not roll.
        d.FONT_VARIANT = d.RANDOM_FONT
        d._current_random_font = "ubuntu"
        d._last_phrase = "half past"
        with mock.patch.object(d, "pick_random_font", return_value="bangers") as pick:
            self.assertEqual(d._resolve_font(None), "ubuntu")
        pick.assert_not_called()

    def test_random_first_render_reuses_init_seed(self):
        # `_init_fonts()` seeds `_current_random_font` to preload the
        # goodnight font; the first clock render then arrives with
        # `_last_phrase=None`. Re-rolling here would burn a slot from the
        # shuffle bag without the user ever seeing the init pick on the
        # clock face, breaking the "all variants before repeats" guarantee.
        d.FONT_VARIANT = d.RANDOM_FONT
        d._current_random_font = "ubuntu"
        d._last_phrase = None
        with mock.patch.object(d, "pick_random_font", return_value="bangers") as pick:
            picked = d._resolve_font("half past")
        self.assertEqual(picked, "ubuntu")
        self.assertEqual(d._last_phrase, "half past")
        pick.assert_not_called()


class ResolveFrameTests(unittest.TestCase):
    """`_resolve_frame` mirrors `_resolve_font`: an explicit frame in config
    wins; the AUTO_FRAME sentinel defers to the active font's category so the
    border stays in step with whichever variant is currently rendering."""

    def setUp(self):
        self._saved_frame = d.FRAME_VARIANT

    def tearDown(self):
        d.FRAME_VARIANT = self._saved_frame

    def test_explicit_frame_wins_over_font_category(self):
        # Even with a rustic-bucket font, an explicit frame in config must be
        # honoured verbatim — that's the whole point of the override.
        d.FRAME_VARIANT = "retro"
        self.assertEqual(d._resolve_frame("unifraktur-maguntia"), "retro")

    def test_auto_frame_resolves_via_font_category(self):
        d.FRAME_VARIANT = d.AUTO_FRAME
        self.assertEqual(d._resolve_frame("unifraktur-maguntia"), "rustic")
        self.assertEqual(d._resolve_frame("vt323"), "retro")
        self.assertEqual(d._resolve_frame("dejavu"), "bauhaus")

    def test_auto_frame_with_unknown_font_falls_back_to_default(self):
        d.FRAME_VARIANT = d.AUTO_FRAME
        from fuzzyclock_core import DEFAULT_FRAME

        self.assertEqual(d._resolve_frame("not-a-real-font"), DEFAULT_FRAME)


class _FakeButton:
    """Minimal `gpiozero.Button` substitute for `button_listener` tests.

    The listener calls `wait_for_press()` once per iteration, then `time.time()`
    twice (start/end) bracketing a `while button.is_pressed: ...` poll loop.
    By keeping `is_pressed` False and feeding paired (start, end) values into
    a mocked `time.time`, we control the computed press duration exactly. After
    the configured durations are exhausted, `wait_for_press()` sets the daemon's
    stop event so the listener exits cleanly instead of looping forever.
    """

    def __init__(self, durations):
        self._remaining = list(durations)
        self.is_pressed = False
        self.time_queue = []
        for dur in durations:
            self.time_queue.extend([0.0, dur])

    def wait_for_press(self):
        if not self._remaining:
            d._stop_event.set()
            return
        self._remaining.pop(0)


def _make_time_fn(queue):
    """Pop from `queue` until exhausted, then return the last popped value.

    The fallthrough matters because `logging` calls `time.time()` to stamp
    every record and we don't want a "pop from empty list" blowup mid-test.
    """
    state = {"last": 0.0}

    def t():
        if queue:
            state["last"] = queue.pop(0)
        return state["last"]

    return t


class ButtonListenerTests(unittest.TestCase):
    """Press classification: long → shutdown, short → render, else ignored."""

    def setUp(self):
        d._stop_event.clear()
        d._on_render_success()

    def tearDown(self):
        d._stop_event.clear()
        d._on_render_success()

    def _run_listener(self, durations, mode="day"):
        button = _FakeButton(durations)
        epd = mock.Mock()
        with (
            mock.patch.object(d.time, "time", side_effect=_make_time_fn(button.time_queue)),
            mock.patch.object(d, "shutdown_procedure") as shutdown,
            mock.patch.object(d, "draw_clock") as draw,
            mock.patch.object(d, "_current_mode_now", return_value=mode),
        ):
            d.button_listener(button, epd)
        return shutdown, draw

    def test_long_press_triggers_shutdown(self):
        shutdown, draw = self._run_listener([d.LONG_PRESS_SECONDS])
        shutdown.assert_called_once()
        draw.assert_not_called()

    def test_long_press_overshoot_still_triggers_shutdown(self):
        shutdown, _ = self._run_listener([d.LONG_PRESS_SECONDS + 2.0])
        shutdown.assert_called_once()

    def test_short_press_forces_render(self):
        # 0.5s sits in the SHORT_PRESS window (0.05, 2.0).
        shutdown, draw = self._run_listener([0.5])
        draw.assert_called_once()
        shutdown.assert_not_called()

    def test_short_press_passes_invert_for_after_hours_mode(self):
        _shutdown, draw = self._run_listener([0.5], mode="after_hours")
        draw.assert_called_once()
        _args, kwargs = draw.call_args
        self.assertTrue(kwargs.get("invert"))

    def test_short_press_during_night_mode_is_ignored(self):
        # The panel is deep-asleep behind the goodnight slide at night; a
        # render would write to a sleeping controller and leave a frozen
        # clock face up until morning (the main loop never repaints goodnight
        # while the mode stays "night").
        shutdown, draw = self._run_listener([0.5], mode="night")
        draw.assert_not_called()
        shutdown.assert_not_called()

    def test_long_press_during_night_mode_still_shuts_down(self):
        # Only the refresh is gated on mode — the user must always be able
        # to power the clock off.
        shutdown, draw = self._run_listener([d.LONG_PRESS_SECONDS], mode="night")
        shutdown.assert_called_once()
        draw.assert_not_called()

    def test_debounce_noise_is_ignored(self):
        # Anything <= SHORT_PRESS_MIN_SECONDS (0.05) is below the noise floor.
        shutdown, draw = self._run_listener([0.01])
        shutdown.assert_not_called()
        draw.assert_not_called()

    def test_mid_range_press_is_ignored(self):
        # Between SHORT_PRESS_MAX (2.0) and LONG_PRESS (5.0) is the deliberate
        # dead zone — long enough to be intentional, short enough not to be a
        # shutdown hold.
        shutdown, draw = self._run_listener([3.0])
        shutdown.assert_not_called()
        draw.assert_not_called()

    def test_render_failure_increments_counter(self):
        button = _FakeButton([0.5])
        with (
            mock.patch.object(d.time, "time", side_effect=_make_time_fn(button.time_queue)),
            mock.patch.object(d, "draw_clock", side_effect=RuntimeError("SPI")),
            mock.patch.object(d, "_current_mode_now", return_value="day"),
        ):
            d.button_listener(button, mock.Mock())
        self.assertEqual(d._consecutive_failures, 1)

    def test_fatal_render_failure_sets_stop_event(self):
        # Pre-bump the counter to one short of fatal so a single failure here
        # crosses the threshold and signals main to exit.
        for _ in range(d.RENDER_RETRY_FATAL - 1):
            d._on_render_failure()
        button = _FakeButton([0.5])
        with (
            mock.patch.object(d.time, "time", side_effect=_make_time_fn(button.time_queue)),
            mock.patch.object(d, "draw_clock", side_effect=RuntimeError("SPI")),
            mock.patch.object(d, "_current_mode_now", return_value="day"),
        ):
            d.button_listener(button, mock.Mock())
        self.assertTrue(d._stop_event.is_set())

    def test_stop_event_set_during_wait_aborts_iteration(self):
        # If _stop_event flips between wait_for_press() and the early-return
        # check, the listener must exit without firing any action.
        class StopOnWait:
            is_pressed = False

            def wait_for_press(self_inner):
                d._stop_event.set()

        with (
            mock.patch.object(d, "shutdown_procedure") as shutdown,
            mock.patch.object(d, "draw_clock") as draw,
        ):
            d.button_listener(StopOnWait(), mock.Mock())
        shutdown.assert_not_called()
        draw.assert_not_called()


class ButtonSupervisorTests(unittest.TestCase):
    """`_button_supervisor` must restart on crash and exit cleanly on stop."""

    def setUp(self):
        d._stop_event.clear()

    def tearDown(self):
        d._stop_event.clear()

    def test_restarts_listener_after_crash(self):
        calls = []

        def fake_listener(button, epd):
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError("listener crashed")
            # Second invocation: signal clean exit so the supervisor returns.
            d._stop_event.set()

        with (
            mock.patch.object(d, "button_listener", fake_listener),
            mock.patch.object(d._stop_event, "wait", return_value=False),
        ):
            d._button_supervisor(mock.Mock(), mock.Mock())
        self.assertEqual(len(calls), 2)

    def test_stop_event_during_backoff_exits_cleanly(self):
        # Listener always crashes; supervisor must NOT loop forever — when
        # _stop_event.wait() returns True (event set), it exits.
        def fake_listener(button, epd):
            raise RuntimeError("permanent crash")

        with (
            mock.patch.object(d, "button_listener", fake_listener),
            mock.patch.object(d._stop_event, "wait", return_value=True) as wait_mock,
        ):
            d._button_supervisor(mock.Mock(), mock.Mock())
        wait_mock.assert_called_once_with(10)


class ShutdownProcedureTests(unittest.TestCase):
    """The three steps must be independently guarded — a goodnight or sleep
    failure must not prevent the shutdown command from running. The command
    goes through `sudo -n` because the unit runs the daemon as a non-root
    user, whom polkit denies a bare `shutdown`."""

    _SHUTDOWN_ARGV = ["sudo", "-n", "shutdown", "-h", "now"]

    def _run_mock(self):
        return mock.Mock(return_value=mock.Mock(returncode=0))

    def test_invokes_shutdown_command(self):
        epd = mock.Mock()
        run_mock = self._run_mock()
        with (
            mock.patch.object(d, "display_goodnight"),
            mock.patch.object(d, "run", run_mock),
        ):
            d.shutdown_procedure(epd)
        epd.sleep.assert_called_once()
        run_mock.assert_called_once_with(self._SHUTDOWN_ARGV)

    def test_goodnight_failure_still_sleeps_and_shuts_down(self):
        epd = mock.Mock()
        run_mock = self._run_mock()
        with (
            mock.patch.object(d, "display_goodnight", side_effect=RuntimeError("panel hang")),
            mock.patch.object(d, "run", run_mock),
        ):
            d.shutdown_procedure(epd)
        epd.sleep.assert_called_once()
        run_mock.assert_called_once_with(self._SHUTDOWN_ARGV)

    def test_sleep_failure_still_shuts_down(self):
        epd = mock.Mock()
        epd.sleep.side_effect = RuntimeError("SPI gone")
        run_mock = self._run_mock()
        with (
            mock.patch.object(d, "display_goodnight"),
            mock.patch.object(d, "run", run_mock),
        ):
            d.shutdown_procedure(epd)
        run_mock.assert_called_once_with(self._SHUTDOWN_ARGV)

    def test_both_failures_still_shut_down(self):
        epd = mock.Mock()
        epd.sleep.side_effect = RuntimeError("SPI gone")
        run_mock = self._run_mock()
        with (
            mock.patch.object(d, "display_goodnight", side_effect=RuntimeError("panel hang")),
            mock.patch.object(d, "run", run_mock),
        ):
            d.shutdown_procedure(epd)
        run_mock.assert_called_once_with(self._SHUTDOWN_ARGV)

    def test_failed_shutdown_command_logs_an_error(self):
        # A denied sudo (missing sudoers rule) must surface in the journal,
        # not vanish silently — it's the only breadcrumb the user gets.
        run_mock = mock.Mock(return_value=mock.Mock(returncode=1))
        with (
            mock.patch.object(d, "display_goodnight"),
            mock.patch.object(d, "run", run_mock),
            self.assertLogs(level="ERROR") as captured,
        ):
            d.shutdown_procedure(mock.Mock())
        self.assertTrue(any("sudoers" in msg for msg in captured.output))

    def test_successful_shutdown_command_logs_no_error(self):
        run_mock = self._run_mock()
        with (
            mock.patch.object(d, "display_goodnight"),
            mock.patch.object(d, "run", run_mock),
            mock.patch.object(d.logging, "error") as error_mock,
        ):
            d.shutdown_procedure(mock.Mock())
        error_mock.assert_not_called()


class ConcurrentRenderCounterTests(unittest.TestCase):
    """The counter is shared between the main loop and button thread, so the
    lock must keep increments atomic under contention."""

    def setUp(self):
        d._on_render_success()

    def tearDown(self):
        d._on_render_success()

    def test_concurrent_failures_are_counted_atomically(self):
        per_thread = 100
        n_threads = 8

        def worker():
            for _ in range(per_thread):
                d._on_render_failure()

        threads = [threading.Thread(target=worker) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(d._consecutive_failures, per_thread * n_threads)
        self.assertTrue(d._needs_recovery)


class SunTimesCacheTests(unittest.TestCase):
    """`_sun_times_cached` is an LRU on top of the pure NOAA helper; it must
    return identical objects on a hit and recompute on a miss."""

    def setUp(self):
        d._sun_times_cached.cache_clear()

    def test_cache_hits_for_repeated_args(self):
        args = (date(2024, 6, 21), 51.5074, -0.1278)
        first = d._sun_times_cached(*args)
        second = d._sun_times_cached(*args)
        info = d._sun_times_cached.cache_info()
        self.assertEqual(info.hits, 1)
        self.assertEqual(info.misses, 1)
        # tuple identity confirms the cached object was returned, not recomputed.
        self.assertIs(first, second)

    def test_cache_miss_for_new_date(self):
        d._sun_times_cached(date(2024, 6, 21), 51.5074, -0.1278)
        d._sun_times_cached(date(2024, 6, 22), 51.5074, -0.1278)
        info = d._sun_times_cached.cache_info()
        self.assertEqual(info.misses, 2)
        self.assertEqual(info.hits, 0)

    def test_cache_clear_resets_stats(self):
        d._sun_times_cached(date(2024, 6, 21), 51.5074, -0.1278)
        d._sun_times_cached.cache_clear()
        info = d._sun_times_cached.cache_info()
        self.assertEqual(info.hits, 0)
        self.assertEqual(info.misses, 0)
        self.assertEqual(info.currsize, 0)


class _FakeEPD:
    """Test double for the Waveshare EPD — records every SPI-shaped call.

    Mirrors the small surface that `reset_base_image`, `display_goodnight`,
    and `draw_clock` actually touch: width/height (the panel is portrait, so
    landscape callers swap to epd.height/epd.width), getbuffer (opaque blob),
    and the four display/init/sleep methods.
    """

    def __init__(self):
        self.width = 122
        self.height = 250
        self.calls = []
        self.last_part_base = None
        self.last_partial = None
        self.last_display = None

    def getbuffer(self, image):
        return ("buf", image.size, image.mode)

    def displayPartBaseImage(self, buf):
        self.calls.append(("part_base", buf))
        self.last_part_base = buf

    def displayPartial(self, buf):
        self.calls.append(("partial", buf))
        self.last_partial = buf

    def display(self, buf):
        self.calls.append(("display", buf))
        self.last_display = buf

    def init(self):
        self.calls.append(("init",))

    def sleep(self):
        self.calls.append(("sleep",))


class ResetBaseImageTests(unittest.TestCase):
    def test_seeds_base_image_with_white_background(self):
        epd = _FakeEPD()
        d.reset_base_image(epd, invert=False)
        self.assertEqual([c[0] for c in epd.calls], ["part_base"])
        # getbuffer was handed an image of (width, height) == (epd.height, epd.width).
        _tag, size, mode = epd.last_part_base
        self.assertEqual(size, (epd.height, epd.width))
        self.assertEqual(mode, "1")

    def test_inverted_base_image_uses_black_background(self):
        epd = _FakeEPD()
        d.reset_base_image(epd, invert=True)
        # Same SPI shape; the difference (background colour) is internal to
        # the rendered buffer. Asserting the call shape is what we can test
        # at this seam without a pixel comparator.
        self.assertEqual([c[0] for c in epd.calls], ["part_base"])


class _FontFixtureMixin:
    """Tests that exercise a real render path need fonts populated. The
    daemon defers font loading to main(); tests do it explicitly."""

    @classmethod
    def setUpClass(cls):
        d._init_fonts()

    @classmethod
    def tearDownClass(cls):
        d.font_large = None
        d.font_small = None
        d.font_tiny = None
        d.font_goodnight = None


class DisplayGoodnightTests(_FontFixtureMixin, unittest.TestCase):
    def test_uses_full_display_call_not_partial(self):
        epd = _FakeEPD()
        # display() blocks on a 2s sleep at the end; skip it.
        with mock.patch.object(d.time, "sleep"):
            d.display_goodnight(epd)
        kinds = [c[0] for c in epd.calls]
        self.assertIn("display", kinds)
        self.assertNotIn("partial", kinds)


class DrawClockTests(_FontFixtureMixin, unittest.TestCase):
    def setUp(self):
        # Pre-seed _last_applied_frame so draw_clock doesn't trigger an
        # implicit reset_base_image on the first call; the tests below assert
        # what draw_clock does in steady state, not on cold start.
        self._saved_frame = d._last_applied_frame
        d._last_applied_frame = "bauhaus"

    def tearDown(self):
        d._last_applied_frame = self._saved_frame

    def test_uses_partial_refresh(self):
        epd = _FakeEPD()
        d.draw_clock(epd, invert=False)
        self.assertEqual([c[0] for c in epd.calls], ["partial"])

    def test_inverted_render_still_uses_partial(self):
        epd = _FakeEPD()
        d.draw_clock(epd, invert=True)
        self.assertEqual([c[0] for c in epd.calls], ["partial"])

    def test_frame_change_reseeds_base_before_partial(self):
        # Random-font + auto-frame can shift the frame between renders. If
        # draw_clock didn't reseed the partial-refresh base in that case,
        # displayPartial would diff against the old frame and ghost the old
        # border. Simulate the shift by pre-seeding a non-bauhaus frame and
        # forcing _resolve_frame to return bauhaus for this render.
        d._last_applied_frame = "rustic"
        epd = _FakeEPD()
        with mock.patch.object(d, "_resolve_frame", return_value="bauhaus"):
            d.draw_clock(epd, invert=False)
        self.assertEqual([c[0] for c in epd.calls], ["part_base", "partial"])
        self.assertEqual(d._last_applied_frame, "bauhaus")

    def test_concurrent_calls_keep_part_base_paired_with_partial(self):
        # draw_clock runs from both the main loop and the button thread. If
        # the _last_applied_frame check isn't held under the same lock as the
        # subsequent reseed + render + displayPartial, two concurrent calls
        # can interleave: e.g. [part_base_A, part_base_B, partial_A, partial_B]
        # which leaves partial_A diffing against B's base. Under _render_lock
        # the pairs stay atomic regardless of scheduler ordering.
        import itertools
        import threading as _t

        epd = _FakeEPD()
        # Cycle through non-bauhaus frames so every draw_clock call sees a
        # frame mismatch and triggers a reset_base_image.
        d._last_applied_frame = "bauhaus"

        cycle = itertools.cycle(["rustic", "sketchy"])
        cycle_lock = _t.Lock()

        def _frame(_variant):
            with cycle_lock:
                return next(cycle)

        # Patch once in the main thread (not inside the workers) so the
        # mock's enter/exit can't race across threads and leave d._resolve_frame
        # pointing at a stale mock after the test finishes.
        with mock.patch.object(d, "_resolve_frame", side_effect=_frame):
            threads = [_t.Thread(target=lambda: d.draw_clock(epd, invert=False)) for _ in range(8)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        # Every part_base must be immediately followed by its own partial
        # before the next part_base — that's the atomic pair the lock guards.
        kinds = [c[0] for c in epd.calls]
        for i, kind in enumerate(kinds):
            if kind == "part_base":
                self.assertLess(i + 1, len(kinds), "trailing part_base with no partial")
                self.assertEqual(
                    kinds[i + 1],
                    "partial",
                    f"part_base at {i} not immediately followed by partial: {kinds}",
                )


class RequireFontsTests(unittest.TestCase):
    """`_require_fonts` exists so a missed `_init_fonts()` fails loudly
    instead of letting PIL silently fall back to its default bitmap font."""

    def test_raises_when_fonts_uninitialized(self):
        saved = d.font_large
        d.font_large = None
        try:
            with self.assertRaises(AssertionError):
                d._require_fonts()
        finally:
            d.font_large = saved

    def test_passes_when_fonts_initialized(self):
        d._init_fonts()
        try:
            d._require_fonts()  # must not raise
        finally:
            d.font_large = None
            d.font_small = None
            d.font_tiny = None
            d.font_goodnight = None


class MainSignalHandlerTests(unittest.TestCase):
    """The SIGTERM/SIGINT handler that main() registers must set _stop_event.

    main() can't run end-to-end without hardware, so we mock all EPD/GPIO
    calls and let the loop complete one tick (by having _stop_event.wait
    set the event as its side-effect). We then extract the handler that was
    registered via signal.signal and call it directly to confirm it behaves
    correctly.
    """

    def setUp(self):
        d._stop_event.clear()
        d._on_render_success()
        self._saved = {
            "DIALECT": d.DIALECT,
            "FONT_VARIANT": d.FONT_VARIANT,
            "FRAME_VARIANT": d.FRAME_VARIANT,
            "LATITUDE": d.LATITUDE,
            "LONGITUDE": d.LONGITUDE,
            "AFTER_HOURS_ENABLED": d.AFTER_HOURS_ENABLED,
            "font_goodnight": d.font_goodnight,
        }

    def tearDown(self):
        d._stop_event.clear()
        d._on_render_success()
        for attr, val in self._saved.items():
            setattr(d, attr, val)

    def _run_main_and_capture_handlers(self):
        """Run main() with all hardware mocked; return {signum: handler}."""

        registered = {}

        def _capture(signum, handler):
            registered[signum] = handler

        with (
            mock.patch("fuzzyclock_daemon.signal.signal", side_effect=_capture),
            mock.patch("fuzzyclock_daemon.epd2in13_V4") as m_epd,
            mock.patch.object(
                d,
                "_load_config",
                return_value=(d.DEFAULT_DIALECT, d.DEFAULT_FONT, d.AUTO_FRAME, None, None),
            ),
            mock.patch.object(d, "_init_fonts"),
            mock.patch.object(d, "reset_base_image"),
            mock.patch.object(d, "_current_mode_now", return_value="night"),
            mock.patch.object(d, "display_goodnight"),
            # Exit the main loop after the first tick.
            mock.patch.object(
                d._stop_event,
                "wait",
                side_effect=lambda timeout: d._stop_event.set(),
            ),
        ):
            m_epd.EPD.return_value = mock.Mock()
            d.main()

        return registered

    def test_sigterm_is_registered_and_sets_stop_event(self):
        import signal as _sig

        registered = self._run_main_and_capture_handlers()
        self.assertIn(_sig.SIGTERM, registered)
        d._stop_event.clear()
        registered[_sig.SIGTERM](_sig.SIGTERM, None)
        self.assertTrue(d._stop_event.is_set())

    def test_sigint_is_registered_and_sets_stop_event(self):
        import signal as _sig

        registered = self._run_main_and_capture_handlers()
        self.assertIn(_sig.SIGINT, registered)
        d._stop_event.clear()
        registered[_sig.SIGINT](_sig.SIGINT, None)
        self.assertTrue(d._stop_event.is_set())


class MainLoopTests(unittest.TestCase):
    """Drive `main()`'s control flow through a scripted sequence of modes.

    The MainSignalHandlerTests sister class above only exercises the night
    branch (and the SIGTERM/SIGINT handlers). This class fills in the rest of
    the loop body — mode transitions that reseed the partial-refresh base
    image, the every-5-minute render cadence, the `_needs_recovery` re-init
    path after consecutive failures, the fatal-threshold break, and the
    cleanup epd.sleep() that runs after the loop exits.

    Strategy: mock `_current_mode_now` with a scripted iterator over modes;
    after the iterator is exhausted, set `_stop_event` so main() exits. Drop
    in mocks for `draw_clock`, `display_goodnight`, `reset_base_image`, and
    `epd2in13_V4` so we can assert their call sequences and inject failures.
    """

    def setUp(self):
        d._stop_event.clear()
        d._on_render_success()
        self._saved = {
            "DIALECT": d.DIALECT,
            "FONT_VARIANT": d.FONT_VARIANT,
            "FRAME_VARIANT": d.FRAME_VARIANT,
            "LATITUDE": d.LATITUDE,
            "LONGITUDE": d.LONGITUDE,
            "AFTER_HOURS_ENABLED": d.AFTER_HOURS_ENABLED,
            "font_goodnight": d.font_goodnight,
        }

    def tearDown(self):
        d._stop_event.clear()
        d._on_render_success()
        for attr, val in self._saved.items():
            setattr(d, attr, val)

    def _run_main(
        self,
        mode_sequence,
        draw_side_effect=None,
        force_render_every_tick=True,
        goodnight_side_effect=None,
    ):
        """Run main() driving _current_mode_now through `mode_sequence`.

        Returns (fake_epd, m_draw, m_goodnight, m_reset, mode_calls). After
        the last mode is returned, _stop_event is set so the next iteration
        of `while not _stop_event.is_set()` exits — giving exactly
        len(mode_sequence) iterations. `force_render_every_tick=True` pins
        the wall-clock minute to a multiple of 5 so the should_render check
        fires on every tick even when the mode doesn't change — needed for
        the recovery / fatal-threshold tests where the mode is constant.
        """
        epd = _FakeEPD()

        modes = list(mode_sequence)
        if not modes:
            self.fail("mode_sequence must contain at least one mode")
        total_calls = [0]
        loop_iter = [0]
        mode_calls = []

        def mode_fn():
            # main() calls _current_mode_now() once before the loop to pick
            # the initial reset_base_image invert, then again on each loop
            # iteration. We hand the first call modes[0] without consuming
            # it, so mode_sequence semantically describes LOOP iterations.
            total_calls[0] += 1
            if total_calls[0] == 1:
                return modes[0]
            i = loop_iter[0]
            if i >= len(modes):
                d._stop_event.set()  # defensive
                return modes[-1]
            loop_iter[0] += 1
            mode_calls.append(modes[i])
            if i == len(modes) - 1:
                d._stop_event.set()
            return modes[i]

        m_draw = mock.Mock(side_effect=draw_side_effect)
        m_goodnight = mock.Mock(side_effect=goodnight_side_effect)
        m_reset = mock.Mock()

        # Patch datetime in the daemon module so the minute check is
        # deterministic. Mocking the whole class is heavy-handed but the only
        # caller is `datetime.now().minute` on the render-cadence line.
        m_dt = mock.MagicMock()
        m_dt.now.return_value = mock.Mock(minute=0 if force_render_every_tick else 1)

        with (
            mock.patch("fuzzyclock_daemon.epd2in13_V4") as m_epd_mod,
            mock.patch.object(
                d,
                "_load_config",
                return_value=(d.DEFAULT_DIALECT, d.DEFAULT_FONT, d.AUTO_FRAME, None, None),
            ),
            mock.patch.object(d, "_init_fonts"),
            mock.patch.object(d, "draw_clock", m_draw),
            mock.patch.object(d, "display_goodnight", m_goodnight),
            mock.patch.object(d, "reset_base_image", m_reset),
            mock.patch.object(d, "_current_mode_now", side_effect=mode_fn),
            # Honor the stop event so the loop actually exits after the last
            # scripted mode. Returning the event's state mirrors what real
            # Event.wait does once it's been set.
            mock.patch.object(
                d._stop_event,
                "wait",
                side_effect=lambda timeout=None: d._stop_event.is_set(),
            ),
            mock.patch("fuzzyclock_daemon.signal.signal"),
            # Button is None in CI (no gpiozero backend); the try/except in
            # main() handles that gracefully. Keep it that way so we don't
            # accidentally start a real thread.
            mock.patch("fuzzyclock_daemon.Button", None),
            mock.patch("fuzzyclock_daemon.datetime", m_dt),
        ):
            m_epd_mod.EPD.return_value = epd
            d.main()

        return epd, m_draw, m_goodnight, m_reset, mode_calls

    def test_night_only_uses_display_goodnight_and_skips_draw_clock(self):
        epd, m_draw, m_goodnight, _m_reset, _ = self._run_main(["night"])
        m_goodnight.assert_called_once_with(epd)
        m_draw.assert_not_called()
        # The overnight deep sleep right after the goodnight slide.
        self.assertIn(("sleep",), epd.calls)

    def test_entering_night_deep_sleeps_the_panel_exactly_once(self):
        # The controller goes into deep sleep right after the goodnight
        # slide; the post-loop cleanup must NOT sleep it a second time —
        # epd.sleep() tears down the SPI handle, so a second call would raise.
        epd, _m_draw, m_goodnight, _m_reset, _ = self._run_main(["night"])
        m_goodnight.assert_called_once()
        self.assertEqual(epd.calls.count(("sleep",)), 1)

    def test_waking_from_night_reinits_panel_before_first_render(self):
        # night → day: startup init, overnight sleep, wake-up init, then the
        # loop-exit cleanup sleeps the (now awake) panel again.
        epd, m_draw, _m_goodnight, m_reset, _ = self._run_main(["night", "day"])
        self.assertEqual(
            [c for c in epd.calls if c in (("init",), ("sleep",))],
            [("init",), ("sleep",), ("init",), ("sleep",)],
        )
        m_draw.assert_called_once_with(mock.ANY, invert=False)
        # The wake-up init must come before the base reseed (reset_base_image
        # writes to SPI); both happen, reseed count unchanged from the plain
        # night→day transition.
        self.assertEqual(m_reset.call_count, 2)

    def test_goodnight_failure_skips_the_overnight_sleep(self):
        # If the goodnight render failed, the panel state is unknown — keep
        # the controller awake so the morning render path can recover it.
        # The only sleep is then the post-loop cleanup.
        epd, _m_draw, m_goodnight, _m_reset, _ = self._run_main(
            ["night"],
            goodnight_side_effect=RuntimeError("panel hang"),
        )
        m_goodnight.assert_called_once()
        self.assertEqual(epd.calls.count(("sleep",)), 1)
        # ... and it ran at loop exit, not as the overnight sleep: a wake-up
        # init is never needed because panel_asleep stayed False.
        self.assertEqual(epd.calls.count(("init",)), 1)

    def test_day_mode_invokes_draw_clock_without_invert(self):
        epd, m_draw, m_goodnight, _m_reset, _ = self._run_main(["day"])
        m_draw.assert_called_once_with(epd, invert=False)
        m_goodnight.assert_not_called()

    def test_after_hours_mode_invokes_draw_clock_with_invert(self):
        epd, m_draw, _m_goodnight, _m_reset, _ = self._run_main(["after_hours"])
        m_draw.assert_called_once_with(epd, invert=True)

    def test_mode_change_into_clock_mode_reseeds_base_image(self):
        # day → after_hours flips invert; the partial-refresh base must be
        # re-seeded before the next displayPartial or the inverted clock face
        # will diff against the old (non-inverted) base.
        _epd, m_draw, _m_goodnight, m_reset, _ = self._run_main(["day", "after_hours"])
        # Initial seed (white/day) + the day→after_hours transition seed (black).
        self.assertEqual(m_reset.call_count, 2)
        initial_call, transition_call = m_reset.call_args_list
        self.assertEqual(initial_call.kwargs.get("invert"), False)
        self.assertEqual(transition_call.kwargs.get("invert"), True)
        # Both ticks rendered the clock at their respective inverts.
        self.assertEqual(
            [c.kwargs.get("invert") for c in m_draw.call_args_list],
            [False, True],
        )

    def test_night_to_day_transition_reseeds_base(self):
        # Coming out of night must re-seed the base before the first
        # partial-refresh render of the day, otherwise displayPartial would
        # diff against a base painted around the full-screen goodnight slide.
        _epd, m_draw, m_goodnight, m_reset, _ = self._run_main(["night", "day"])
        m_goodnight.assert_called_once()
        m_draw.assert_called_once_with(mock.ANY, invert=False)
        # Initial seed (white) + the night→day transition seed.
        self.assertEqual(m_reset.call_count, 2)

    def test_day_to_night_transition_runs_goodnight_without_extra_reset(self):
        # Night mode doesn't paint a clock face, so it does NOT reseed the
        # base. The base will be reseeded again on the next morning's first
        # non-night mode (see test_night_to_day_transition_reseeds_base).
        _epd, m_draw, m_goodnight, m_reset, _ = self._run_main(["day", "night"])
        self.assertEqual(m_draw.call_count, 1)
        m_goodnight.assert_called_once()
        # Only the initial seed at startup — no transition-into-night seed.
        self.assertEqual(m_reset.call_count, 1)

    def test_consecutive_failures_trigger_recovery_reinit_before_next_render(self):
        # After RENDER_RETRY_REINIT (3) draw_clock failures, the next render
        # path must re-init the EPD (epd.init() inside epd_lock) and reseed
        # the base before calling draw_clock again. We check this by counting
        # epd.init() invocations in the fake panel's call log: the panel
        # records one init at the top of main() (the real epd.init() call,
        # which we don't mock), so we expect one MORE init after the 4th
        # tick fires the recovery path.
        call_count = [0]

        def failing_then_succeeding(*_args, **_kwargs):
            call_count[0] += 1
            if call_count[0] <= d.RENDER_RETRY_REINIT:
                raise RuntimeError("simulated SPI hiccup")
            # success on the 4th attempt

        epd, m_draw, _m_goodnight, m_reset, _ = self._run_main(
            ["day"] * (d.RENDER_RETRY_REINIT + 1),
            draw_side_effect=failing_then_succeeding,
        )
        # 4 draw attempts total: 3 failures + 1 recovered success.
        self.assertEqual(m_draw.call_count, d.RENDER_RETRY_REINIT + 1)
        # Initial reset + the recovery reset before the 4th draw.
        self.assertGreaterEqual(m_reset.call_count, 2)
        # The recovery path re-inits the panel inside epd_lock; the fake
        # records ("init",). Startup init plus the recovery init = 2.
        init_calls = [c for c in epd.calls if c == ("init",)]
        self.assertEqual(len(init_calls), 2, f"expected one recovery init; got {epd.calls}")

    def test_fatal_threshold_breaks_main_loop(self):
        # RENDER_RETRY_FATAL (10) consecutive failures must break out of the
        # main loop so systemd can restart us with a clean slate, rather
        # than burning through StartLimitBurst with stale state.
        def always_fails(*_args, **_kwargs):
            raise RuntimeError("simulated permanent SPI failure")

        # Provide more ticks than the fatal threshold so we can be sure the
        # loop broke on its own rather than at sequence exhaustion.
        epd, m_draw, _m_goodnight, _m_reset, mode_calls = self._run_main(
            ["day"] * (d.RENDER_RETRY_FATAL + 5),
            draw_side_effect=always_fails,
        )
        # The loop must have broken at exactly RENDER_RETRY_FATAL failures —
        # not consumed the extra ticks we provided.
        self.assertEqual(m_draw.call_count, d.RENDER_RETRY_FATAL)
        self.assertLess(len(mode_calls), d.RENDER_RETRY_FATAL + 5)
        # Cleanup must still run on the fatal-break path.
        self.assertIn(("sleep",), epd.calls)

    def test_cleanup_sleeps_epd_after_normal_loop_exit(self):
        # Stop-event-driven shutdown (SIGTERM/SIGINT path) must call
        # epd.sleep() so the panel doesn't burn in. We verify by running
        # one night tick and confirming sleep() lands in the fake's log.
        epd, _m_draw, _m_goodnight, _m_reset, _ = self._run_main(["day"])
        self.assertEqual(epd.calls[-1], ("sleep",))

    def test_cleanup_sleep_failure_does_not_propagate(self):
        # The final epd.sleep() is wrapped in try/except so an SPI hiccup
        # during shutdown can't poison the exit path.
        epd = _FakeEPD()
        epd.sleep = mock.Mock(side_effect=RuntimeError("sleep failed"))

        def mode_fn():
            d._stop_event.set()
            return "day"

        with (
            mock.patch("fuzzyclock_daemon.epd2in13_V4") as m_epd_mod,
            mock.patch.object(
                d,
                "_load_config",
                return_value=(d.DEFAULT_DIALECT, d.DEFAULT_FONT, d.AUTO_FRAME, None, None),
            ),
            mock.patch.object(d, "_init_fonts"),
            mock.patch.object(d, "draw_clock"),
            mock.patch.object(d, "reset_base_image"),
            mock.patch.object(d, "_current_mode_now", side_effect=mode_fn),
            mock.patch.object(d._stop_event, "wait", return_value=False),
            mock.patch("fuzzyclock_daemon.signal.signal"),
            mock.patch("fuzzyclock_daemon.Button", None),
        ):
            m_epd_mod.EPD.return_value = epd
            d.main()  # must not raise

        epd.sleep.assert_called_once()

    def test_after_hours_enabled_logs_coordinates(self):
        # When _load_config returns lat/lon, main() must log the after-hours
        # banner. We assert by inspecting the logging output.
        epd = _FakeEPD()

        def mode_fn():
            d._stop_event.set()
            return "day"

        with (
            mock.patch("fuzzyclock_daemon.epd2in13_V4") as m_epd_mod,
            mock.patch.object(
                d,
                "_load_config",
                return_value=(d.DEFAULT_DIALECT, d.DEFAULT_FONT, d.AUTO_FRAME, 51.5, -0.1),
            ),
            mock.patch.object(d, "_init_fonts"),
            mock.patch.object(d, "draw_clock"),
            mock.patch.object(d, "display_goodnight"),
            mock.patch.object(d, "reset_base_image"),
            mock.patch.object(d, "_current_mode_now", side_effect=mode_fn),
            mock.patch.object(d._stop_event, "wait", return_value=False),
            mock.patch("fuzzyclock_daemon.signal.signal"),
            mock.patch("fuzzyclock_daemon.Button", None),
            self.assertLogs("root", level="INFO") as cm,
        ):
            m_epd_mod.EPD.return_value = epd
            d.main()

        self.assertTrue(
            any("After-hours mode enabled" in msg for msg in cm.output),
            f"expected after-hours banner; got {cm.output}",
        )
        self.assertTrue(d.AFTER_HOURS_ENABLED)

    def test_after_hours_disabled_when_coords_missing(self):
        # No coords → after-hours stays off and the disabled-banner is logged.
        epd = _FakeEPD()

        def mode_fn():
            d._stop_event.set()
            return "day"

        with (
            mock.patch("fuzzyclock_daemon.epd2in13_V4") as m_epd_mod,
            mock.patch.object(
                d,
                "_load_config",
                return_value=(d.DEFAULT_DIALECT, d.DEFAULT_FONT, d.AUTO_FRAME, None, None),
            ),
            mock.patch.object(d, "_init_fonts"),
            mock.patch.object(d, "draw_clock"),
            mock.patch.object(d, "display_goodnight"),
            mock.patch.object(d, "reset_base_image"),
            mock.patch.object(d, "_current_mode_now", side_effect=mode_fn),
            mock.patch.object(d._stop_event, "wait", return_value=False),
            mock.patch("fuzzyclock_daemon.signal.signal"),
            mock.patch("fuzzyclock_daemon.Button", None),
            self.assertLogs("root", level="INFO") as cm,
        ):
            m_epd_mod.EPD.return_value = epd
            d.main()

        self.assertTrue(
            any("After-hours mode disabled" in msg for msg in cm.output),
            f"expected after-hours-disabled banner; got {cm.output}",
        )
        self.assertFalse(d.AFTER_HOURS_ENABLED)

    def test_systemexit_when_epd_driver_missing(self):
        # If the waveshare_epd driver is not importable, main() must refuse
        # to start with a clear message rather than NameError'ing later.
        with mock.patch("fuzzyclock_daemon.epd2in13_V4", None):
            with self.assertRaises(SystemExit):
                d.main()


if __name__ == "__main__":
    unittest.main()
