#!/bin/bash
# Deploy LittleFuzzyClock on a fresh Raspberry Pi.
# Run from the repo root: bash deploy.sh
#
# Idempotent: re-running upgrades the unit file in place and restarts the
# service. Safe to invoke after editing fuzzyclock.service or pulling new
# code. Exits non-zero with a journal tail if the service fails to come up.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_USER="${SUDO_USER:-$USER}"
SERVICE_NAME="fuzzyclock.service"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"

# Friendly preflight: deploy needs root for apt + systemctl. Re-exec under
# sudo if we can rather than failing partway through.
if [[ $EUID -ne 0 ]]; then
    if command -v sudo >/dev/null 2>&1; then
        echo "==> Re-running under sudo..."
        exec sudo -E SUDO_USER="$TARGET_USER" bash "$0" "$@"
    else
        echo "ERROR: deploy.sh needs root (for apt and systemctl). Run as root or install sudo." >&2
        exit 1
    fi
fi

echo "==> Installing system packages..."
# Python deps come from apt rather than pip so we don't collide with PEP 668
# (externally-managed-environment) on Raspberry Pi OS Bookworm+.
# Fonts are vendored under fonts/ so no font packages are required here.
apt-get update -qq
apt-get install -y \
    python3-pil \
    python3-yaml \
    python3-gpiozero \
    python3-spidev \
    python3-rpi.gpio

echo "==> Checking SPI..."
# `lsmod | grep` is the runtime check; `raspi-config nonint do_spi 0` flips
# the boot-config flag so SPI is enabled on the next boot. We do both so a
# fresh image picks it up even if the module isn't loaded yet.
SPI_REBOOT_REQUIRED=0
if lsmod | grep -q '^spi_bcm2835\b'; then
    echo "    SPI module already loaded."
elif command -v raspi-config >/dev/null 2>&1; then
    raspi-config nonint do_spi 0
    SPI_REBOOT_REQUIRED=1
    echo "    SPI enabled via raspi-config — reboot required before the display works."
else
    echo "    WARNING: spi_bcm2835 not loaded and raspi-config not available."
    echo "    Enable SPI manually (add 'dtparam=spi=on' to /boot/firmware/config.txt) before starting the service."
fi

echo "==> Installing $SERVICE_NAME (user=$TARGET_USER, dir=$REPO_DIR)..."
# Render the unit file to a tempfile, then move into place atomically. This
# prevents a partial write from leaving systemd with a malformed unit if the
# script is interrupted mid-tee.
TMP_UNIT="$(mktemp)"
trap 'rm -f "$TMP_UNIT"' EXIT
sed \
    -e "s|__REPO_DIR__|$REPO_DIR|g" \
    -e "s|__USER__|$TARGET_USER|g" \
    "$REPO_DIR/systemd/$SERVICE_NAME" \
    > "$TMP_UNIT"
install -m 0644 "$TMP_UNIT" "$SERVICE_PATH"

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
# `restart` (not `start`) so re-running picks up edits to the unit file or
# any pulled-in code changes without needing a manual stop first.
systemctl restart "$SERVICE_NAME"

echo "==> Verifying service is active..."
# Give it a few seconds to either come up or fail; an immediate is-active
# check after restart can race with the service still starting.
sleep 3
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "    OK: $SERVICE_NAME is active."
else
    echo "ERROR: $SERVICE_NAME failed to start. Recent journal output:" >&2
    journalctl -u "$SERVICE_NAME" --no-pager -n 50 >&2 || true
    echo "" >&2
    echo "Full status:" >&2
    systemctl status "$SERVICE_NAME" --no-pager >&2 || true
    exit 1
fi

echo ""
echo "Done. Service status:"
systemctl status "$SERVICE_NAME" --no-pager
if [[ $SPI_REBOOT_REQUIRED -eq 1 ]]; then
    echo ""
    echo "NOTE: SPI was just enabled — reboot to activate it before the display will respond."
fi
