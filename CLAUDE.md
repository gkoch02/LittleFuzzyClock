# CLAUDE.md

Rules for Claude Code sessions on this repo. User-facing usage is in the README.

**Keep this file short.** Add a line only for a non-obvious invariant or footgun, and keep it to one line. The *why* goes in a code comment or docstring, once; this file points there. Don't restate what a reader gets from the code in seconds.

## Layout

- `fuzzyclock_core.py` — facade re-exporting the public API of `fuzzyclock/`. Entry points and tests import from it; don't duplicate implementations.
- `fuzzyclock/` — `sun`, `dialects`, `fonts`, `frames` are leaf modules with no intra-package imports; `render` is the only one that imports the others.
- `fuzzyclock_daemon.py` — the systemd daemon. `fuzzyclock_preview.py` — dev/dry-run CLI.
- `fuzzyclock_config.yaml` — the daemon's only config, read once in `main()` by `_load_config()`.
- `fonts/` — vendored font files. `docs/fonts.md` + `docs/previews/` — the font catalog.
- `waveshare_epd/` — vendored driver. Don't edit except to sync upstream; ruff skips it.

## Commands

- Tests: `python3 -m unittest discover` from the repo root. One module: `python3 -m unittest tests.test_render`.
- Lint/format: `ruff check . && ruff format .` (CI runs `ruff format --check`).
- Render check: `python3 fuzzyclock_preview.py --dry-run --output /tmp/out.png [--time HH:MM --font NAME --dialect NAME]`.
- Needs Pillow and PyYAML; fonts are vendored in `fonts/`. Off-Pi only: `pip install -r requirements.txt`.

## Rules

**Imports and patching**
- The facade re-exports public names only. Import private names (`_CONTENT_PAD`, `_fit_body_font`, …) from their owning module.
- `mock.patch` must target the owning module. Patching `fuzzyclock_core.<name>` silently does nothing.
- Nothing that loads fonts or reads config may run at import time (`load_font` raises `SystemExit`). `tests/test_daemon_import.py` enforces this in a fresh interpreter.
- The hardware import guards in the daemon and `fuzzyclock_preview._load_epd` are deliberately `except Exception`. Don't narrow them; see the comment above the daemon's imports. The preview must never import the driver for `--dry-run`.

**Daemon**
- Every EPD driver call goes through `_call_with_timeout(..., lock=epd_lock)` (see its docstring). Never take `epd_lock` yourself. Check `_epd_init()` for a `-1` return.
- A new render path must call `_on_render_success()` / `_on_render_failure()`. Exception: the night-transition handlers deliberately only log.
- Any mode transition or full `epd.display()` leaves the partial-refresh base stale. Call `reset_base_image()`.
- `current_mode()` stays pure. `day_start`/`day_end` are for tests; don't wire them to globals.
- Display writes are `.rotate(180)`'d at the SPI boundary, not in `render_clock`.
- The shutdown button uses `sudo -n shutdown`. `deploy.sh` installs the NOPASSWD rule; polkit denies a bare `shutdown`.

**Phrasing and rendering**
- `fuzzy_time()`'s `min(..., 11)` is intentional: minutes 57–59 read "almost [next hour]". Don't "simplify" it.
- A dialect's `hour_advance_at` must be in `1..11`; `_validate_dialects` enforces it at import.
- Layout constants in `fuzzyclock/render.py` / `frames.py` are locked in by `tests.test_render.RenderClockOverflowTests`. Run it after touching them.
- The goodnight slide always uses `GOODNIGHT_FONT` and the rustic frame, whatever the configured font is.

**Fonts**
- Adding a font variant takes four touches: `FONT_VARIANTS`, `FONT_FRAME_CATEGORY`, the comment block in `fuzzyclock_config.yaml`, and a `docs/fonts.md` row (plus a preview PNG if the font is vendored).
- `_VENDORED_FONT_DIR` walks up two directories from `fuzzyclock/fonts.py`. Keep that if the file moves.

**Tests**
- Every test module must pass on its own; CI runs each one alone as well as the full suite.
- A test simulating a hung driver call must use a throwaway lock, not `epd_lock` (see `BusyPinTimeoutTests`). The abandoned worker never releases it.
- A test comment says what is checked, not why the code does it; point at the code comment instead of restating it.
- Prefer table-driven tests with `subTest` (see `tests/test_fuzzy_time.py`) over a new class per feature.

## CI and deploy

- `.github/rulesets/main.json` requires the checks `lint`, `test (3.11)` and `test (3.12)` by exact name, with no bypass. Never rename those jobs or add a matrix axis to `test`, or `main` locks. That is why `test-pillow-floor` is a separate job; keep its exact Pillow pin in step with `requirements.txt`.
- Keep ruff's `target-version = "py39"`. Bumping it lets UP017 rewrite `timezone.utc` → `UTC`, which breaks 3.9/3.10.
- `deploy.sh` installs Python deps through apt, not pip (PEP 668). It is idempotent and substitutes `__REPO_DIR__` / `__USER__` in the unit file. Don't hardcode `/home/pi`.
- There is no `.timer`. The unit has `Restart=always`, and the daemon handles day/night itself.
