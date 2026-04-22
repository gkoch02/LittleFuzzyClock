# Little Fuzzy Clock

A fuzzy clock for a Raspberry Pi Zero driving a [Waveshare 2.13" e-ink display (V4)](https://www.waveshare.com/wiki/2.13inch_e-Paper_HAT_%28E%29).

Instead of showing an exact time, it displays natural-language phrases like "quarter past nine am" or "twenty to three pm". A small Bauhaus-inspired border decorates the frame. The date is shown as a footer.

## Hardware

- Raspberry Pi Zero (or any Pi with SPI)
- Waveshare 2.13" e-Paper HAT V4 (122×250, black/white)
- GPIO pin 3 wired to a push button for manual refresh / shutdown

## Files

| File | Purpose |
|------|---------|
| `fuzzyclock_daemon.py` | Production daemon — runs continuously, updates every 5 min, handles day/night mode and button presses |
| `fuzzyClock2.py` | Standalone script — useful for development; supports `--dry-run` to render to a PNG without hardware |
| `systemd/fuzzyclock.service` | systemd service unit |
| `systemd/fuzzyclock.timer` | systemd timer (starts clock at 7 AM) |
| `waveshare_epd/` | Waveshare e-Paper Python library (MIT license, from [Waveshare's e-Paper repo](https://github.com/waveshare/e-Paper)) |

## Behaviour

- **Day mode (7 AM – 10:59 PM):** display updates every 5 minutes via partial refresh
- **Night mode (11 PM – 6:59 AM):** shows "Goodnight" and the display sleeps
- **Short button press (0.05–2 s):** forces an immediate refresh
- **Long button press (≥ 5 s):** graceful shutdown (`shutdown -h now`)

## Setup

### 1. Enable SPI

```bash
sudo raspi-config  # Interface Options → SPI → Enable
```

### 2. Install dependencies

```bash
sudo apt install python3-pip python3-pil fonts-dejavu-core
pip3 install gpiozero spidev RPi.GPIO
```

### 3. Install the Waveshare library

```bash
cd waveshare_epd
# The library is included in this repo — no extra install needed.
# Just make sure to run scripts from the repo root so Python finds the package.
```

### 4. Install the systemd service

```bash
sudo cp systemd/fuzzyclock.service /etc/systemd/system/
sudo cp systemd/fuzzyclock.timer   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now fuzzyclock.service
```

### 5. Test without hardware (dry run)

```bash
python3 fuzzyClock2.py --dry-run --output preview.png
```

## License

Project code: MIT. Waveshare library files in `waveshare_epd/` are copyright Waveshare, also MIT licensed.
