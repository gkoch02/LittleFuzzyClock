#!/bin/bash
# Deploy LittleFuzzyClock on a fresh Raspberry Pi.
# Run from the repo root: bash deploy.sh
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_USER="${SUDO_USER:-$USER}"

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

echo "==> Installing systemd unit (user=$TARGET_USER, dir=$REPO_DIR)..."
sed \
    -e "s|__REPO_DIR__|$REPO_DIR|g" \
    -e "s|__USER__|$TARGET_USER|g" \
    "$REPO_DIR/systemd/fuzzyclock.service" \
    | sudo tee /etc/systemd/system/fuzzyclock.service > /dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now fuzzyclock.service

echo ""
echo "Done. Service status:"
systemctl status fuzzyclock.service --no-pager
