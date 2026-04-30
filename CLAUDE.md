# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Notes for Claude Code sessions on this repo. Keep it short — the README covers user-facing usage.

## Layout

- `fuzzyclock_core.py` — single source of truth for time phrasing (`fuzzy_time`, `DIALECTS`), font loading, the clock-face drawing (`render_clock`, `draw_border`), and the NOAA sunrise/sunset approximation (`sun_times`). Both entry points import from it; do not reintroduce duplicate copies.
- `fuzzyclock_daemon.py` — long-running daemon, invoked by systemd. Handles the day/after_hours/night state machine, partial refresh, GPIO button, render-failure recovery, and graceful SIGTERM/SIGINT.
- `fuzzyClock2.py` — dev/dry-run script. `--dry-run` renders to PNG and works on any Linux/macOS box; `--dialect` picks a phrasing.
- `fuzzyclock_config.json` — `latitude`/`longitude` for after-hours mode. Missing/malformed → after-hours mode disabled, daemon stays on plain day/night.
- `systemd/fuzzyclock.service` — templated unit. `__REPO_DIR__` and `__USER__` are sed-substituted by `deploy.sh`.
- `waveshare_epd/` — vendored driver. Don't edit unless syncing upstream from Waveshare; ruff is configured to skip it (`extend-exclude` in `pyproject.toml`).

## Tests & lint

- Run everything: `python3 -m unittest discover`. Single file: `python3 -m unittest test_fuzzy_time` (or `-v` for verbose). Single test: `python3 -m unittest test_daemon.CurrentModeTests.test_polar_midnight_sun_falls_back_to_day`.
- Lint: `ruff check .` (CI runs this; config is in `pyproject.toml`, `target-version = "py39"` — don't bump it without checking that UP017 doesn't rewrite `timezone.utc` → `UTC`, which breaks 3.9/3.10).
- PIL is needed (transitively via `fuzzyclock_core`); install with `pip install Pillow` or apt's `python3-pil`. DejaVu fonts must be present too (`fonts-dejavu-core`) or `load_font()` will exit.
- `test_fuzzy_time.py` — pure-logic cases for `fuzzy_time()`, including dialect tables. Add cases here when touching the phrasing logic.
- `test_render.py` — smoke tests for `draw_border` and `render_clock`. Asserts ink-on-canvas, not pixel-exact output, to stay font-version stable.
- `test_sun.py` — pins the `sun_times` NOAA approximation against published sunrise/sunset values (tolerance ±5 min) and the polar-night / midnight-sun branches.
- `test_daemon.py` — pure-function tests for `current_mode`, `_sleep_to_next_tick`, `_load_coordinates`, `_resolve_dialect`, and the cross-thread render-retry counter. Imports `fuzzyclock_daemon` directly; the module's hardware imports are guarded so this works on CI without GPIO/EPD.
- `test_daemon_import.py` — bare `import fuzzyclock_daemon` smoke test. Catches eager hardware calls at module scope that would crash on CI before the unit tests get a chance to run.
- `test_dry_run.py` — invokes `fuzzyClock2.py --dry-run` as a subprocess and validates the PNG. Exercises the EPD-not-available fallback.
- Manual render check: `python3 fuzzyClock2.py --dry-run --output /tmp/out.png`.
- CI: `.github/workflows/test.yml` runs ruff plus the full suite on Python 3.11 and 3.12 on every push and PR.

## Deploy path

- `deploy.sh` installs Python deps via `apt` (`python3-pil`, `python3-gpiozero`, …), **not** pip. Bookworm's PEP 668 blocks pip against the system Python. `requirements.txt` is for off-Pi dev environments only.
- The systemd service file uses `__REPO_DIR__` and `__USER__` sentinels; `deploy.sh` substitutes them via `sed` using the invoking user (`${SUDO_USER:-$USER}`) and the repo's actual location. Don't hardcode `/home/pi` or `User=pi` back in.
- There is intentionally no `.timer` file — the unit has `Restart=always` (`RestartSec=10`, `StartLimitBurst=5`/`StartLimitIntervalSec=300`) and the daemon handles day/night internally.

## Daemon architecture

- **Mode state machine.** `current_mode(now, lat, lon, after_hours_enabled, day_start=DAY_START_HOUR, day_end=DAY_END_HOUR)` returns `"day"`, `"after_hours"`, or `"night"`. Outside the wake window (`DAY_START_HOUR..DAY_END_HOUR`, currently 7..23) it's always night. Inside the window, the sun decides between day and after_hours; with no coordinates (or polar night/midnight sun) it falls back to plain day. Keep this function pure — `_current_mode_now()` is the wrapper that reads module globals; the `day_start`/`day_end` kwargs exist for tests, don't wire them to module globals.
- **Tick cadence.** Main loop wakes every `TICK_INTERVAL` (60 s) for mode-transition latency, but only re-renders on a mode change or on a 5-minute wall-clock boundary (`UPDATE_INTERVAL=300`). `_sleep_to_next_tick` aligns sleeps with wall-clock multiples to eliminate cumulative drift; its result is always in `(0, interval]` (never zero — that would busy-loop).
- **Partial-refresh base image.** `epd.displayPartial` diffs against the last `displayPartBaseImage`. Any full `epd.display()` (e.g. goodnight) and any normal/inverted swap leaves the base stale, so call `reset_base_image(epd, invert=…)` on every mode transition. The `_sun_times_cached` LRU keeps the ephemeris stable for the day.
- **Render-failure recovery.** Failures from both the main loop and the button thread feed a shared counter (`_render_state_lock`). After `RENDER_RETRY_REINIT` (3) consecutive failures, the next render path re-inits the EPD and reseeds the base image. After `RENDER_RETRY_FATAL` (10), the daemon exits and lets systemd restart it. `_on_render_success()` clears both flags. If you add a new render path, call both helpers.
- **Button thread supervision.** The button listener runs under `_button_supervisor`, which catches exceptions and restarts the listener after a 10s backoff. Without it, a silent crash in the button thread would leave the daemon running with no button input — and since the main process is still alive, systemd wouldn't restart it. The supervisor exits cleanly when `_stop_event` is set.
- **Dialect resolution.** `FUZZYCLOCK_DIALECT` env var, validated against `DIALECTS`; unknown values log a warning and fall back to `classic`. The daemon reads it once in `main()` (not at import time) so tests can import the module without side effects.

## Gotchas

- Fonts: `fuzzyclock_core.load_font()` tries a Pi path then macOS fallbacks. If you add a new font size, use `load_font()` — never call `ImageFont.truetype()` directly at module scope (that's what made the daemon crash on import before).
- E-ink display is mounted upside down; all writes are `.rotate(180)`'d just before `epd.display*()`. Keep that at the SPI boundary, not inside `render_clock`.
- `epd_lock` guards every SPI write in the daemon. If you add a new path that talks to `epd`, wrap it. The signal handler does no I/O and acquires no locks — it just sets `_stop_event` so the main loop can exit cleanly without deadlocking against an in-flight render.
- `fuzzy_time()` caps the 5-minute bucket at 11 on purpose — minutes 57–59 must read "almost [next hour]", not wrap back to "just after [current hour]". There's a test for this in every dialect; don't "simplify" the `min(..., 11)`.
- Dialect `hour_advance_at` must stay in `1..11`. There's a module-load-time guard in `fuzzyclock_core.py` that raises `ValueError` if a dialect violates this — it'd silently break the "almost [next hour]" invariant via `% 12`. If you add a new dialect that needs an early advance (like German's `5`), keep it within the range.
- Hardware imports (`gpiozero`, `waveshare_epd`) catch both `ImportError` *and* `RuntimeError` — gpiozero raises `RuntimeError` on non-Pi Linux when it can't find a GPIO backend. Don't narrow the except clause.
- Daemon module-level config (`DIALECT`, `LATITUDE`, `LONGITUDE`, `AFTER_HOURS_ENABLED`) is populated in `main()`, not at import time, so `import fuzzyclock_daemon` in tests doesn't trigger filesystem reads or warning logs. Keep it that way.
