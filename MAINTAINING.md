# Keeping Little Fuzzy Clock running

A guide to running the clock day to day, with nothing but a terminal and a text editor: checking it's healthy, changing its settings, updating, recovering when something breaks, and making small code changes safely.

`README.md` is the full reference. This page only tells you which of it you need, and when. The paths below assume the repo was cloned into the home folder of the user `pi`; `systemctl cat fuzzyclock` shows the real ones.

## What's where

The clock is a Raspberry Pi running one background service called `fuzzyclock`. It runs all the time: every minute it checks whether it's day, after-hours or night, and every five minutes it redraws the time.

| Thing | Where on the Pi | Touch it? |
|---|---|---|
| The code (a copy of this GitHub repo) | `~/LittleFuzzyClock` | Only through `git pull`, or small tweaks (see the last section) |
| **Your settings** | `~/LittleFuzzyClock/fuzzyclock_config.yaml` | Yes, this is the file you edit. It's also part of the code, which matters when updating (see "Updating") |
| The fonts | `~/LittleFuzzyClock/fonts/` | Only to add a licensed commercial font (`docs/fonts.md`) |
| Python and its libraries | The Pi's own system Python, installed with `apt` by `deploy.sh` | Rarely |
| The service definition | `/etc/systemd/system/fuzzyclock.service` | Rarely; `deploy.sh` writes it |
| Permission for the button to shut the Pi down | `/etc/sudoers.d/fuzzyclock` | No |

Nothing else is stored: the clock keeps no state between restarts. Everything below starts with logging in to the Pi from your Mac (`ssh pi@<the Pi>`, or the shortcut in your `~/.ssh/config`) and `cd ~/LittleFuzzyClock`.

## Is it OK?

```bash
systemctl status --no-pager fuzzyclock
```

`Active: active (running)` is good. Anything else, see "When it stops working".

```bash
journalctl -u fuzzyclock --since today --no-pager
```

A healthy day is quiet: a line when the service starts (`After-hours mode enabled …`), then one line at each change of mode (`Entering after-hours mode.`, `Entering night mode.`, `Entering day mode.`). Redraws aren't logged. Lines with `failed` or `ERROR` are the ones to read; `draw_clock() failed (1/10)` now and then is the clock recovering from a panel hiccup by itself.

To watch live (Ctrl-C to stop watching; the clock keeps running): `journalctl -u fuzzyclock -f`.

## Changing settings (no code)

All the choices live in one file, read when the service starts. The recipe is always the same:

```bash
cp fuzzyclock_config.yaml ~/fuzzyclock_config.yaml.bak-$(date +%Y%m%d)                       # 1. back it up
nano fuzzyclock_config.yaml                                                                     # 2. edit
python3 -c "import yaml; yaml.safe_load(open('fuzzyclock_config.yaml')); print('config OK')"    # 3. check it
sudo systemctl restart fuzzyclock                                                               # 4. restart
journalctl -u fuzzyclock -n 10 --no-pager                                                       # 5. check what it read
```

Step 3 checks the file is readable YAML: it prints `config OK`, or an error naming the line. Step 5 catches the rest. The clock never refuses to start over a setting: a name it doesn't know (`Unknown font='litterata'`) falls back to the default with a warning, a bad coordinate turns after-hours mode off with a warning, and an unreadable file makes it run on all defaults. So if a change seems to have no effect, the log says why.

The settings, each listed with every option in the file's own comments:

| Setting | What it does | Example |
|---|---|---|
| `dialect` | The wording: `classic`, `shakespeare`, `klingon`, `belter`, `german`, `hal`, `cthulhu`, `latin` | `dialect: shakespeare` |
| `font` | The typeface, or `random` for a new one each time the words change. `docs/fonts.md` shows them all | `font: literata` |
| `frame` | The border: `auto` (matches the font), `bauhaus`, `rustic`, `sketchy`, `retro` | `frame: auto` |
| `latitude`, `longitude` | Where you are, for sunset; set both to `null` to turn after-hours mode off | `latitude: 51.4769` |

The hours (day from 07:00, Goodnight from 23:00) and the five-minute redraw aren't settings; they're `DAY_START_HOUR`, `DAY_END_HOUR` and `UPDATE_MINUTES` near the top of `fuzzyclock_daemon.py`.

To see a setting before putting it on the clock, try it on the Mac first (`docs/CODE_TOUR.md`, "Making a change"): `--font`, `--dialect` and `--frame` take the same values.

**To undo**, copy your backup back and restart:

```bash
cp ~/fuzzyclock_config.yaml.bak-YYYYMMDD fuzzyclock_config.yaml
sudo systemctl restart fuzzyclock
```

## The button

| Press | Does |
|---|---|
| Short (under 2 seconds) | Redraw now (ignored at night, when the panel is asleep) |
| Hold 5 seconds | Shut the Pi down safely. Press again to start it back up |

Use the long press before unplugging the Pi. Pulling the power while it's writing can corrupt the SD card, which is the most common way a Pi dies.

## Updating

Your settings file is part of the repo, so git won't update while it holds your changes. Set it aside, update, and put it back:

```bash
cd ~/LittleFuzzyClock
cp fuzzyclock_config.yaml ~/fuzzyclock_config.yaml.mine
git checkout -- fuzzyclock_config.yaml
git pull --ff-only origin main
cp ~/fuzzyclock_config.yaml.mine fuzzyclock_config.yaml
sudo systemctl restart fuzzyclock
systemctl status --no-pager fuzzyclock
```

If the update added a new option, its comment won't be in your copy; `git diff` after the last `cp` shows what the new version of the file has that yours doesn't. If the update changed `deploy.sh` or `systemd/fuzzyclock.service`, run `bash deploy.sh` again too; it's safe to re-run and keeps your settings.

**To go back to the version that worked**: this repo has no release tags, so use the commit list. `git log --oneline -10` shows the last ten changes, newest first. Pick the one before the update, then do the same set-aside dance with `git checkout <its short code>` in place of `git pull`. `git checkout main` and the update steps put you back on the latest.

## When it stops working

| What you see | Try |
|---|---|
| Time frozen on the panel | `systemctl status fuzzyclock`. If it's not running, `sudo systemctl restart fuzzyclock`, then `journalctl -u fuzzyclock -n 50` for the reason |
| `failed` with `start-limit-hit` | It crashed five times in five minutes and systemd gave up. Read the log for why, fix it, then `sudo systemctl reset-failed fuzzyclock && sudo systemctl start fuzzyclock` |
| `draw_clock() failed` over and over, `EPDTimeoutError` | The panel isn't answering: usually the ribbon cable. Reseat it with the Pi shut down |
| `epd.init() failed` | The panel can't be reached: SPI off (`sudo raspi-config nonint get_spi` prints `0` when it's on) or the cable |
| `GPIO busy` | Another program has the display pins. Only one program may drive the panel; `ps aux \| grep python` shows what's running |
| A setting didn't take effect | `journalctl -u fuzzyclock -n 20` right after a restart shows the warning |
| Inverted face at the wrong time | Check `latitude`/`longitude`, and the Pi's time zone: `timedatectl` |
| Button does nothing | `journalctl -u fuzzyclock \| grep -iE "press|button"` shows whether presses arrive. A long press that logs `shutdown command failed` means `/etc/sudoers.d/fuzzyclock` is missing; `bash deploy.sh` reinstalls it |
| Fails after a Pi system update | See "Things that will break eventually" |
| Can't log in to the Pi | Its network address changed; your router's device list shows the new one. Update `~/.ssh/config` on the Mac |
| Pi won't boot at all | Probably the SD card. See "Rebuilding from scratch" |

## Back up now, while it works

There's one file to keep, your settings. From a Mac terminal:

```bash
mkdir -p ~/Backups/LittleFuzzyClock
scp 'pi@<the Pi>:LittleFuzzyClock/fuzzyclock_config.yaml' ~/Backups/LittleFuzzyClock/
```

If you've added commercial fonts to `fonts/`, copy those too; they're not in the repo.

## Rebuilding from scratch

For a dead SD card or a new Pi. Allow half an hour.

1. Flash Raspberry Pi OS Lite (Bookworm) onto a card with Raspberry Pi Imager on the Mac. In its settings, set the username to `pi`, your Wi-Fi, and turn on SSH.
2. Log in, then get the code:

   ```bash
   sudo apt update && sudo apt install -y git
   git clone https://github.com/gkoch02/LittleFuzzyClock.git ~/LittleFuzzyClock
   ```

3. Put your settings back, from the Mac:

   ```bash
   scp ~/Backups/LittleFuzzyClock/fuzzyclock_config.yaml 'pi@<the Pi>:LittleFuzzyClock/'
   ```

4. Install and start it, back on the Pi:

   ```bash
   cd ~/LittleFuzzyClock
   bash deploy.sh
   ```

   It installs the packages, turns on SPI, installs the service and the button's shutdown permission, and starts the clock. If it says SPI was just enabled, `sudo reboot` once.

## Things that will break eventually

Left alone, the Pi will run for years. What breaks it is change:

- **A big Raspberry Pi OS upgrade** (a new Debian version) brings a new Python and new versions of the libraries the clock uses (`python3-pil`, `python3-yaml`, `python3-gpiozero`). There's no separate environment to strand, so the clock usually survives, but the drawing library can change underneath it. Symptom: the service fails with an error from `PIL`. Simplest of all: don't do major upgrades on an appliance that works.
- **The drawing library (Pillow)** on the Pi is the one Debian ships (9.4 on Bookworm), much older than the one most of the tests on GitHub use. One test job runs on that exact version, so a change that passes on GitHub works with the Pi's Pillow. A new Debian version brings a newer Pillow, and that job's pin should move with it.
- **The SD card** wears out. A spare card and the backup above make this a short job.

The clock needs no internet once it's running: sunset is worked out on the Pi.

## Small code changes

Settings cover most wishes. When they don't, [`docs/CODE_TOUR.md`](docs/CODE_TOUR.md) explains how the code fits together, and small edits are within reach without knowing Python well, as long as you keep to one change at a time and keep git's safety net.

**The safety net.** On the Pi, in `~/LittleFuzzyClock`:

- `git status` lists files you've changed. `fuzzyclock_config.yaml` always shows; that's your settings.
- `git diff` shows exactly what you changed.
- `git checkout -- <file>` throws your change to that file away and puts the original back.

**Trying a change without touching the panel.** On the Mac, `docs/CODE_TOUR.md`, "Making a change", draws a clock face to a picture with the same code.

**Where common things live:**

| To change | Look in |
|---|---|
| A dialect's words | That dialect's entry in `DIALECTS`, `fuzzyclock/dialects.py`. Keep 12 phrases, one per five-minute step |
| Wake-up and bedtime hours | `DAY_START_HOUR`, `DAY_END_HOUR` in `fuzzyclock_daemon.py` |
| How often it redraws | `UPDATE_MINUTES` in `fuzzyclock_daemon.py` |
| The Goodnight slide's font | `GOODNIGHT_FONT` in `fuzzyclock_daemon.py` |
| The date line's format | `day_line = now.strftime(...)` in `render_clock()`, `fuzzyclock/render.py` |

**Getting it onto the Pi.** The quick way is to make the same edit on the Pi itself (`nano ~/LittleFuzzyClock/<file>`) and restart the service. It stays until the next update, which will refuse while your edit is there: `git diff -- <file> > ~/my-change.patch` saves it, `git checkout -- <file>` clears it, and after the pull `git apply ~/my-change.patch` puts it back (if the file hasn't changed underneath it).

The lasting way is to commit it in the repo on GitHub (on a branch, then a pull request, since `main` is protected), and update the Pi. The tests on GitHub will tell you if the change broke something.

**Leave alone:**

- `waveshare_epd/`: the panel maker's driver, copied in unchanged.
- `/etc/sudoers.d/fuzzyclock`: a broken file there locks you out of `sudo`; `deploy.sh` writes it after checking it.
- `/etc/systemd/system/fuzzyclock.service`: generated by `deploy.sh` from `systemd/fuzzyclock.service`; edit that and re-run the script.
