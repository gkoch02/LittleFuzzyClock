# Little Fuzzy Clock

A fuzzy clock for a Raspberry Pi Zero driving a [Waveshare 2.13" e-ink display (V4)](https://www.waveshare.com/wiki/2.13inch_e-Paper_HAT_%28E%29).

Instead of showing an exact time, it displays natural-language phrases like "quarter past nine am" or "twenty to three pm", with the date as a footer and a small Bauhaus-inspired border.

## Hardware

- Raspberry Pi Zero (or any Pi with SPI)
- Waveshare 2.13" e-Paper HAT V4 (122×250, black/white)
- Push button wired to GPIO pin 3 (for manual refresh and shutdown)

## Behaviour

- **Day mode (7 AM – 10:59 PM):** display updates every 5 minutes via partial refresh
- **Night mode (11 PM – 6:59 AM):** shows "Goodnight" and the display sleeps
- **Short button press (0.05–2 s):** forces an immediate refresh
- **Long button press (≥ 5 s):** graceful shutdown (`shutdown -h now`)

## Rebuilding from scratch

Clone the repo to the Pi and run the deploy script:

```bash
cd /home/pi
git clone https://github.com/gkoch02/LittleFuzzyClock.git
cd LittleFuzzyClock
bash deploy.sh
```

That's it. The script installs dependencies, enables SPI, installs the systemd units, and starts the service.

> **Note:** If SPI wasn't already enabled, the script enables it but you may need to reboot once before the display responds.

## Testing without hardware

`fuzzyClock2.py` supports a `--dry-run` mode that renders to a PNG instead of the display — useful for development on a non-Pi machine:

```bash
python3 fuzzyClock2.py --dry-run --output preview.png
```

## Files

| File | Purpose |
|------|---------|
| `fuzzyclock_daemon.py` | Production daemon — runs continuously, handles day/night mode and button presses |
| `fuzzyClock2.py` | Standalone dev script with `--dry-run` PNG output |
| `deploy.sh` | One-shot deploy script for fresh Pi setup |
| `requirements.txt` | Python dependencies |
| `systemd/fuzzyclock.service` | systemd service unit |
| `systemd/fuzzyclock.timer` | systemd timer (starts clock at 7 AM) |
| `waveshare_epd/` | Waveshare e-Paper Python library (MIT, from [Waveshare's e-Paper repo](https://github.com/waveshare/e-Paper)) |

## License

Project code: MIT. Waveshare library files in `waveshare_epd/` are copyright Waveshare, also MIT licensed.
