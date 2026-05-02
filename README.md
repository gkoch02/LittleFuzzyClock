# Little Fuzzy Clock

[![CI](https://github.com/gkoch02/littlefuzzyclock/actions/workflows/test.yml/badge.svg)](https://github.com/gkoch02/littlefuzzyclock/actions/workflows/test.yml)

A fuzzy clock for a Raspberry Pi Zero driving a [Waveshare 2.13" e-ink display (V4)](https://www.waveshare.com/wiki/2.13inch_e-Paper_HAT_%28E%29).

Instead of showing an exact time, it displays natural-language phrases like "quarter past nine am" or "twenty to three pm", with the date as a footer and a small Bauhaus-inspired border.

![Preview of the fuzzy clock display](docs/preview.png)

## Hardware

- Raspberry Pi Zero (or any Pi with SPI)
- Waveshare 2.13" e-Paper HAT V4 (122×250, black/white)
- Push button between GPIO 3 (BCM, physical pin 5) and ground — used for manual refresh and shutdown. GPIO 3 doubles as the Pi's wake-from-halt pin, so the same button can also power the clock back on after a long-press shutdown.

## Tested environment

- **OS:** Raspberry Pi OS Bookworm (Debian 12). The `deploy.sh` script targets Bookworm's PEP 668 model (system Python via `apt`, no `pip install`). Should work on both 32-bit and 64-bit Pi OS, but only 32-bit on a Pi Zero is regularly exercised.
- **Python:** 3.11 (Bookworm system Python). CI also runs on 3.12.
- **Waveshare driver:** `waveshare_epd/` is vendored from [waveshare/e-Paper](https://github.com/waveshare/e-Paper) (`RaspberryPi_JetsonNano/python/lib/waveshare_epd/`), `epd2in13_V4.py` V1.0 dated 2023-06-25 and `epdconfig.py` V1.2. To resync, copy those two files plus `__init__.py` from upstream — don't edit them in place; ruff is configured to skip the directory in `pyproject.toml`.

## Behaviour

- **Day mode (sunrise – sunset, within 7 AM – 10:59 PM):** display updates every 5 minutes via partial refresh, black ink on white
- **After-hours mode (sunset – 10:59 PM):** same clock face but with the colours inverted (white ink on black). Opt-in — see [After-hours mode](#after-hours-mode) below
- **Night mode (11 PM – 6:59 AM):** shows "Goodnight" and the display sleeps
- **Short button press (0.05–2 s):** forces an immediate refresh
- **Long button press (≥ 5 s):** graceful shutdown (`shutdown -h now`)

## Rebuilding from scratch

Clone the repo anywhere on the Pi and run the deploy script. The systemd unit is templated at install time with the invoking user's home directory, so the clock works under any account — there's no need to run as `pi`:

```bash
git clone https://github.com/gkoch02/LittleFuzzyClock.git
cd LittleFuzzyClock
bash deploy.sh
```

That's it. The script installs dependencies via `apt` (Raspberry Pi OS Bookworm's PEP 668 blocks pip from touching the system Python), enables SPI, and installs and starts the `fuzzyclock.service` systemd unit.

> **Note:** If SPI wasn't already enabled, the script enables it for you, but you may need to reboot once before the display responds.

## Testing without hardware

`fuzzyClock2.py` supports a `--dry-run` mode that renders to a PNG instead of the display — useful for development on a non-Pi machine:

```bash
pip install -r requirements.txt   # only needed off-Pi; deploy.sh uses apt on-Pi
python3 fuzzyClock2.py --dry-run --output preview.png
```

## Phrasing personalities

Eight phrasings ship in the box. Examples below all show 9:30 so you can compare across dialects:

| Dialect                | 9:30 reading                       | Notes                                                              |
| ---------------------- | ---------------------------------- | ------------------------------------------------------------------ |
| `classic` (default)    | `half past / nine am`              | Plain English fuzzy time.                                          |
| `shakespeare`          | `'tis half past / nine of the clock` | Archaic English; drops AM/PM (anachronistic).                    |
| `klingon`              | `half past / Hut rep`              | Real tlhIngan Hol numerals; "rep" is Klingon for *hour*.           |
| `belter`               | `half past / nine bell, ya`        | Lang Belta creole from *The Expanse*; nautical "bell" for time.    |
| `german`               | `halb / zehn`                      | Standard High German; "halb" anchors on the *next* hour.           |
| `hal`                  | `MIDPOINT / 0900 HOURS`            | HAL 9000 mission-control patter; 24h numeric for AM/PM clarity.    |
| `cthulhu`              | `the half-hour / the ninth hour`   | Lovecraftian dread; ordinal hours; climaxes with "the stars are right". |
| `latin`                | `media post / hora IX a.m.`        | Roman-numeral hours; real Latin prepositions; *a.m.*/*p.m.* etymology Easter egg. |

Pick one with `--dialect`:

```bash
python3 fuzzyClock2.py --dry-run --dialect shakespeare --output preview.png
```

The daemon reads the same setting from the `FUZZYCLOCK_DIALECT` environment variable. To change it on the Pi, add a line to the systemd unit and restart:

```ini
[Service]
Environment=FUZZYCLOCK_DIALECT=shakespeare
```

Unknown values fall back to `classic` with a warning in the daemon log.

## Fonts

Eight display fonts ship pre-installed by `deploy.sh`, all chosen for legibility on a 122×250 e-ink panel. Each preview shows the same scene (`9:15` in the `classic` dialect) so you can compare side by side:

| Variant            | Preview                                                                                  | Package                | Character                                                  |
| ------------------ | ---------------------------------------------------------------------------------------- | ---------------------- | ---------------------------------------------------------- |
| `dejavu` (default) | ![dejavu preview](docs/preview-dejavu.png)                                               | `fonts-dejavu-core`    | Clean humanist sans — high x-height, broad Unicode.        |
| `dejavu-serif`     | ![dejavu-serif preview](docs/preview-dejavu-serif.png)                                   | `fonts-dejavu`         | Elegant transitional serif companion to DejaVu Sans.       |
| `liberation-serif` | ![liberation-serif preview](docs/preview-liberation-serif.png)                           | `fonts-liberation2`    | Times-metric serif — newspaper feel.                       |
| `roboto-slab`      | ![roboto-slab preview](docs/preview-roboto-slab.png)                                     | `fonts-roboto-slab`    | Chunky slab serif; renders especially crisply on e-ink.    |
| `cantarell`        | ![cantarell preview](docs/preview-cantarell.png)                                         | `fonts-cantarell`      | GNOME's humanist sans; tall x-height, friendly curves.     |
| `ubuntu`           | ![ubuntu preview](docs/preview-ubuntu.png)                                               | `fonts-ubuntu`         | Distinctive warm sans with subtle calligraphic terminals.  |
| `jetbrains-mono`   | ![jetbrains-mono preview](docs/preview-jetbrains-mono.png)                               | `fonts-jetbrains-mono` | Modern monospaced typewriter look.                         |
| `fredoka`          | ![fredoka preview](docs/preview-fredoka.png)                                             | `fonts-fredoka` (or vendored `fonts/Fredoka.ttf`) | Rounded display font — soft, friendly geometric shapes. |

Pick one with `--font`:

```bash
python3 fuzzyClock2.py --dry-run --font roboto-slab --output preview.png
```

The daemon reads the same setting from the `FUZZYCLOCK_FONT` environment variable:

```ini
[Service]
Environment=FUZZYCLOCK_FONT=roboto-slab
```

Unknown values fall back to `dejavu` with a warning in the daemon log. On macOS the dev script falls back to the nearest stock equivalent (Times for the serif variants, Menlo for the mono, Arial Rounded for `fredoka`); the actual variant only renders authentically on the Pi.

To use a font that isn't packaged for apt, drop a TTF into a `fonts/` directory at the repo root — the `fredoka` variant looks for `fonts/Fredoka.ttf` first, before its apt path.

## After-hours mode

After dark, the clock flips to white-on-black so it doesn't glare at you across the room. The daemon computes local sunrise and sunset itself (no network calls) using the coordinates in `fuzzyclock_config.json`:

```json
{
  "latitude": 37.2872,
  "longitude": -121.9500
}
```

Edit those two numbers to match your location and restart the service. If the file is missing or malformed, after-hours mode stays off and the clock keeps the original day/night behaviour.

The schedule becomes: normal clock from sunrise (or wake-up at 7 AM, whichever is later) to sunset, inverted clock from sunset to bedtime at 11 PM, then "Goodnight" until 7 AM. Mode transitions are checked once per refresh tick (every 5 minutes), so the swap happens at the next tick after the sun crosses the horizon.

Sunrise/sunset are computed via NOAA's simplified solar-position equation, accurate to roughly a minute outside polar regions. At extreme latitudes where the sun never rises or never sets on a given day, the daemon stays in normal day mode.

There's also a unit test suite covering the time-phrasing logic and a render smoke test for the clock face:

```bash
python3 -m unittest discover
```

The same suite runs in CI on every push and pull request — see `.github/workflows/test.yml`.

## Files

| File | Purpose |
|------|---------|
| `fuzzyclock_daemon.py` | Production daemon — runs continuously, handles day/night mode and button presses |
| `fuzzyClock2.py` | Standalone dev script with `--dry-run` PNG output |
| `fuzzyclock_core.py` | Shared rendering logic (fuzzy time phrasing, font loading, clock layout) used by both of the above |
| `test_fuzzy_time.py` | Unit tests for `fuzzy_time()` edge cases |
| `test_render.py` | Smoke tests for `draw_border` and `render_clock` |
| `test_dry_run.py` | End-to-end test that invokes `fuzzyClock2.py --dry-run` |
| `test_sun.py` | Unit tests for the sunrise/sunset approximation used by after-hours mode |
| `.github/workflows/test.yml` | CI workflow — runs the whole suite on push/PR |
| `deploy.sh` | One-shot deploy script for fresh Pi setup |
| `fuzzyclock_config.json` | Latitude/longitude for the after-hours sunset/sunrise calculation |
| `requirements.txt` | Python deps for **dev environments** (macOS, etc.); the Pi deploy uses `apt` |
| `systemd/fuzzyclock.service` | systemd service unit (templated — `deploy.sh` substitutes the user and repo path) |
| `waveshare_epd/` | Waveshare e-Paper Python library (MIT, from [Waveshare's e-Paper repo](https://github.com/waveshare/e-Paper)) |

## License

Project code: MIT. Waveshare library files in `waveshare_epd/` are copyright Waveshare, also MIT licensed.
