# CLAUDE.md

Notes for Claude Code sessions on this repo. Keep it short — the README covers user-facing usage.

## Layout

- `fuzzyclock_core.py` — single source of truth for time phrasing, font loading, and the clock-face drawing. Both entry points import from it; do not reintroduce duplicate copies.
- `fuzzyclock_daemon.py` — long-running daemon, invoked by systemd. Handles day/night mode, partial refresh, GPIO button, graceful SIGTERM/SIGINT.
- `fuzzyClock2.py` — dev/dry-run script. `--dry-run` renders to PNG and works on any Linux/macOS box.
- `waveshare_epd/` — vendored driver. Don't edit unless syncing upstream from Waveshare.

## Testing

- Run everything: `python3 -m unittest discover`. PIL is needed (transitively via `fuzzyclock_core`); install with `pip install Pillow` or apt's `python3-pil`. DejaVu fonts must be present too (`fonts-dejavu-core`) or `load_font()` will exit.
- `test_fuzzy_time.py` — pure-logic cases for `fuzzy_time()`. Add cases here when touching the phrasing logic.
- `test_render.py` — smoke tests for `draw_border` and `render_clock`. Asserts ink-on-canvas, not pixel-exact output, to stay font-version stable.
- `test_dry_run.py` — invokes `fuzzyClock2.py --dry-run` as a subprocess and validates the PNG. Exercises the EPD-not-available fallback.
- Manual render check: `python3 fuzzyClock2.py --dry-run --output /tmp/out.png`. On non-Pi Linux the waveshare driver's import raises `RuntimeError`, which the `try/except` already handles.
- CI: `.github/workflows/test.yml` runs the full suite on Python 3.11 and 3.12 on every push and PR.

## Deploy path

- `deploy.sh` installs Python deps via `apt` (`python3-pil`, `python3-gpiozero`, …), **not** pip. Bookworm's PEP 668 blocks pip against the system Python. `requirements.txt` is for off-Pi dev environments only.
- The systemd service file uses `__REPO_DIR__` and `__USER__` sentinels; `deploy.sh` substitutes them via `sed` using the invoking user (`${SUDO_USER:-$USER}`) and the repo's actual location. Don't hardcode `/home/pi` or `User=pi` back in.
- There is intentionally no `.timer` file — the service has `Restart=always` and the daemon handles day/night internally.

## Gotchas

- Fonts: `fuzzyclock_core.load_font()` tries a Pi path then macOS fallbacks. If you add a new font size, use `load_font()` — never call `ImageFont.truetype()` directly at module scope (that's what made the daemon crash on import before).
- E-ink display is mounted upside down; all writes are `.rotate(180)`'d just before `epd.display*()`. Keep that at the SPI boundary, not inside `render_clock`.
- `epd_lock` guards every SPI write in the daemon. If you add a new path that talks to `epd`, wrap it.
- `fuzzy_time()` caps the 5-minute bucket at 11 on purpose — minutes 57–59 must read "almost [next hour]", not wrap back to "just after [current hour]". There's a test for this; don't "simplify" the `min(..., 11)`.
