# A tour of the code

For anyone opening this repo for the first time. The README is the reference; this page is meant to be read once, top to bottom, and leaves you knowing which few files matter, how "quarter past nine am" gets onto the panel, and how to find your way around the rest.

You don't need to know Python well to follow it. Where a piece of Python is quoted, the sentence around it says what it does.

## The big picture

There are two programs here, sharing one set of drawing code:

1. **The daemon** (`fuzzyclock_daemon.py`). It runs on the Pi all the time as the `fuzzyclock` service: wakes every minute, redraws the clock every five, switches between day, after-hours and night, and listens to the button.
2. **The preview** (`fuzzyclock_preview.py`). It draws the same clock face to a PNG on any computer, for trying things out. It never touches the panel with `--dry-run`.

Both get their drawing from the `fuzzyclock/` package, through `fuzzyclock_core.py`, a short file that only re-exports the package's public names so there's one place to import them from.

The rest: `fonts/` (the typefaces, copied in), `waveshare_epd/` (the panel maker's driver, copied in), `fuzzyclock_config.example.yaml` (the default settings; a device's own are in an untracked `fuzzyclock_config.yaml`), `systemd/fuzzyclock.service` and `deploy.sh` (installing it on a Pi), `docs/` (the font catalogue and README pictures), `tests/`.

## Words this code uses

| Word | Means |
|---|---|
| **fuzzy time** | The time in words, rounded to five minutes: "twenty past", "almost". `fuzzy_time()` returns two lines, the phrase and the hour |
| **phrase**, **hour line** | The two lines of the clock face: "quarter past" / "nine am" |
| **dialect** | A set of phrases and hour words: `classic`, `shakespeare`, `klingon`, … Each is an entry in `DIALECTS` in `fuzzyclock/dialects.py` |
| **`hour_advance_at`** | Which five-minute step the hour line moves on to the next hour ("twenty-five *to ten*"). Most dialects switch at 35 past; German at 25 past |
| **font variant** | A name for a typeface, like `literata` or `dejavu`, mapped to its files in `FONT_VARIANTS` (`fuzzyclock/fonts.py`) |
| **vendored** | Copied into the repo rather than installed: the fonts and the panel driver |
| **random font**, **bag** | `font: random` shuffles every vendored font into a "bag" and deals one per new phrase, so each is used once before any repeats |
| **frame** | The decorative border: `bauhaus`, `rustic`, `sketchy` or `retro` (`fuzzyclock/frames.py`). `auto` picks the one that suits the font's category |
| **mode** | `day` (black on white), `after_hours` (white on black, after sunset) or `night` (the "Goodnight" slide, 23:00 to 07:00). `current_mode()` decides |
| **after-hours** | The inverted face between sunset and bedtime. Needs `latitude` and `longitude` to work out sunset; off without them |
| **EPD** | Electronic paper display: the panel. `epd2in13_V4` is this model, 250×122 pixels |
| **partial refresh** | Redrawing only what changed, quickly and without a black flash. It works against a **base image** that must be re-sent whenever the background or the frame changes (`reset_base_image`) |
| **full refresh** | Redrawing the whole panel with a flash; used for the Goodnight slide |
| **tick** | One pass of the daemon's once-a-minute loop |
| **re-init**, **recovery** | Resetting the panel after a failed draw. Three failures in a row trigger a re-init; ten make the daemon exit so systemd restarts it |

## Following one redraw

Say it's 09:15 on a sunny morning. Here's the path, with the file and the function at each step. To find a function, search the file for `def` and its name, e.g. `def draw_clock(`.

**1. The service is already running.** systemd started `fuzzyclock_daemon.py` at boot (`systemd/fuzzyclock.service`, `Restart=always`). On start, `main()` read the settings once with `_load_config()`, from `fuzzyclock_config.yaml` or, if there isn't one, `fuzzyclock_config.example.yaml` (`_config_path()`), loaded the fonts, woke the panel and started a thread that listens to the button.

**2. The loop wakes.** In `main()`, the `while not _stop_event.is_set():` loop runs once a minute. It asks `_current_mode_now()`, which calls `current_mode()`: between 07:00 and 23:00, and with the sun up (`sun_times()` in `fuzzyclock/sun.py` works out sunrise and sunset from the coordinates, with no internet), it's `day`.

**3. Time to draw?** It draws when the mode has just changed, or when the minute is a multiple of five:

```python
should_render = last_state != mode or datetime.now().minute % UPDATE_MINUTES == 0
```

15 is a multiple of 5, so yes.

**4. Pick the words.** `draw_clock()` calls `fuzzy_time(9, 15, "classic")` in `fuzzyclock/dialects.py`. It rounds the minute to the nearest five (15 → step 3), looks up step 3 in the dialect's list of phrases ("quarter past"), and works out the hour line ("nine am"). Past `hour_advance_at` it uses the next hour instead, so 9:40 is "twenty to ten am".

**5. Pick the font and frame.** `_resolve_font()` returns the configured font, or deals the next one from the bag under `font: random`. `_resolve_frame()` turns `auto` into the frame for that font's category. If the frame differs from the last one, `reset_base_image()` sends a fresh base image first.

**6. Draw the face.** `render_clock()` in `fuzzyclock/render.py`, onto a blank 250×122 black-and-white picture. It fits the date line ("Thursday, Nov 12") at the bottom, then `_fit_body_font()` tries sizes from 40 points down until both lines fit inside the frame, then it draws the border (`draw_border()` in `fuzzyclock/frames.py`) and the three lines of text, centred.

**7. Onto the panel.** Back in `draw_clock()`: the picture is turned upside down (the panel is mounted that way) and sent with a partial refresh through `_call_with_timeout(epd.displayPartial, …)`. Every call into the driver goes through `_call_with_timeout`, which gives up after ten seconds, so a loose ribbon cable shows up as a logged failure instead of a frozen clock.

**8. Book-keeping.** `_on_render_success()` clears the failure count. If the draw had failed, `_on_render_failure()` would count it, and the next draw would re-initialise the panel first. Then the loop sleeps until the next minute.

**At sunset** the mode becomes `after_hours`: the next tick sends an inverted base image and draws white on black. **At 23:00** it becomes `night`: `display_goodnight()` draws "Goodnight" in the rustic frame with a full refresh, and the panel goes to sleep until 07:00.

**The button** is handled in `button_listener()`: a short press calls `draw_clock()` straight away; holding it five seconds calls `shutdown_procedure()`, which shows the Goodnight slide, puts the panel to sleep and halts the Pi.

## The files that matter

| File | One line |
|---|---|
| `fuzzyclock_daemon.py` | The service: settings, the minute loop, modes, the button, talking to the panel |
| `fuzzyclock/dialects.py` | Every dialect's words, and `fuzzy_time()` |
| `fuzzyclock/render.py` | Laying out the clock face: `render_clock()` |
| `fuzzyclock/fonts.py` | Font names → files, loading, and the random bag |
| `fuzzyclock/frames.py` | The four borders, and which font gets which |
| `fuzzyclock/sun.py` | Sunrise and sunset for after-hours mode |
| `fuzzyclock_preview.py` | Drawing a face to a PNG for testing |
| `fuzzyclock_config.example.yaml` | The default settings, with every option listed in its comments. Copied to `fuzzyclock_config.yaml` (gitignored) to change them |

## What you can skip

- **`fonts/`** and **`docs/previews/`**: the typefaces and a picture of each. `docs/fonts.md` is the catalogue.
- **`waveshare_epd/`**: the panel maker's driver, copied in unchanged.
- **The commercial-font and Mac-font paths in `fuzzyclock/fonts.py`**: fallbacks for fonts that aren't in the repo; the Pi uses the vendored ones.
- **The timeout and recovery machinery** in the daemon (`_call_with_timeout`, `_needs_recovery`, the button supervisor): it keeps the clock running through hardware hiccups; it doesn't change what you see.
- **`tests/`**: it exists to catch mistakes; ignore it until a test fails.

The care around the panel, and rules like "every driver call goes through one function", look heavy for a clock. They're there because the code was written mostly by an AI, which rereads everything every time and benefits from tests and rules that catch it drifting. A person can safely read around them.

## Finding things

From the repo folder:

```bash
grep -rn "quarter past" fuzzyclock/              # where does this text come from?
grep -rn "def render_clock" .                     # where is this function defined?
grep -rln "GOODNIGHT_FONT" --include='*.py' .       # which files use this name?
```

`-r` searches every file in the folder, `-n` shows line numbers, `-l` lists just the file names. In VS Code or another editor, "Find in Files" (Cmd-Shift-F) does the same, and Cmd-clicking a function name jumps to where it's defined.

## Reading a crash

When something goes wrong, Python prints a **traceback**: the chain of function calls that led to the error. On the Pi it's in `journalctl -u fuzzyclock`. The daemon catches most errors, logs them and carries on, so you'll usually find the traceback under a line like `draw_clock() failed (1/10).` A made-up example of a stuck panel:

```
ERROR draw_clock() failed (1/10).
Traceback (most recent call last):
  File "/home/pi/LittleFuzzyClock/fuzzyclock_daemon.py", line 753, in main
    draw_clock(epd, invert=invert)
  File "/home/pi/LittleFuzzyClock/fuzzyclock_daemon.py", line 516, in draw_clock
    _call_with_timeout(epd.displayPartial, epd.getbuffer(image.rotate(180)), lock=epd_lock)
  File "/home/pi/LittleFuzzyClock/fuzzyclock_daemon.py", line 317, in _call_with_timeout
    raise EPDTimeoutError(
fuzzyclock_daemon.EPDTimeoutError: displayPartial() did not return within 10s (EPD BUSY pin likely stuck)
```

Read it **from the bottom up**:

- The last line is the error: the panel didn't answer within ten seconds.
- The lines above it say where: in `_call_with_timeout`, called from `draw_clock` while sending a partial refresh.
- Everything higher up is how the program got there.

| Error | Usually means |
|---|---|
| `EPDTimeoutError` | The panel stopped answering: usually a loose ribbon cable |
| `epd.init() failed (returned -1)` | The panel can't be reached at all: SPI off, or the cable |
| `GPIO busy`, `waveshare_epd is unavailable` | Another program has the display pins. Only one program can drive the panel |
| `Unknown font=… / dialect=… / frame=…` | A typo in the settings; it fell back to the default (a warning, not a crash) |
| `invalid latitude/longitude` | A typo in the coordinates; after-hours mode is off until it's fixed |
| `ModuleNotFoundError: No module named 'x'` | A system package is missing; see `MAINTAINING.md` |
| `SyntaxError` / `IndentationError` | A hand edit broke the Python. Lines in the same block must line up exactly |

## Making a change

1. **Find the place** with the tables above, or `grep`.
2. **Change one thing.**
3. **Try it** without the panel (on a Mac, once: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`, or just Pillow and PyYAML):

   ```bash
   .venv/bin/python fuzzyclock_preview.py --dry-run --time 09:30 --font literata --dialect shakespeare --output /tmp/clock.png
   open /tmp/clock.png
   ```

   That draws 9:30 in Shakespeare's words in Literata, through the same `render_clock()` the daemon uses. Try different `--time`, `--font`, `--dialect` and `--frame` values; `--help` lists them all.
4. **Undo** if it's wrong: `git diff` shows what you changed, `git checkout -- <file>` puts the original back.

Then run the tests: `.venv/bin/python -m unittest discover` runs them all in seconds; `.venv/bin/python -m unittest tests.test_fuzzy_time` runs one file. If you changed a layout number in `render.py` or `frames.py`, run `tests.test_render` in particular: it checks the text stays inside the frame for every font.

`MAINTAINING.md` covers getting a change onto the Pi.

## Where to go next

| To understand | Read |
|---|---|
| Behaviour, hardware, dialects, fonts, frames, after-hours | `README.md` |
| Every font, with a picture | `docs/fonts.md` |
| The rules for changing the code | `CLAUDE.md` |
| Running it on a Pi | `MAINTAINING.md` |
