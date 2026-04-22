#!/bin/bash
# Deploy LittleFuzzyClock on a fresh Raspberry Pi.
# Run from the repo root: bash deploy.sh
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Installing system packages..."
# Python deps come from apt rather than pip so we don't collide with PEP 668
# (externally-managed-environment) on Raspberry Pi OS Bookworm+.
sudo apt-get update -qq
sudo apt-get install -y \
    fonts-dejavu-core \
    python3-pil \
    python3-gpiozero \
    python3-spidev \
    python3-rpi.gpio

echo "==> Enabling SPI (requires reboot if not already enabled)..."
if ! lsmod | grep -q spi_bcm2835; then
    sudo raspi-config nonint do_spi 0
    echo "    SPI enabled — you may need to reboot before the display works."
fi

echo "==> Installing systemd units..."
sudo cp "$REPO_DIR/systemd/fuzzyclock.service" /etc/systemd/system/
sudo cp "$REPO_DIR/systemd/fuzzyclock.timer"   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now fuzzyclock.service

echo ""
echo "Done. Service status:"
systemctl status fuzzyclock.service --no-pager
