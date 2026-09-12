#!/bin/bash
# ============================================================
# PocketScan install script — run once on the Raspberry Pi
# Usage: bash scripts/install.sh
# ============================================================
set -e

POCKETSCAN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo ""
echo "========================================================"
echo "  PocketScan — Install Script"
echo "  Project dir: $POCKETSCAN_DIR"
echo "========================================================"
echo ""

# ── 1. System packages ────────────────────────────────────────
echo "[1/5] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends \
    python3-pip \
    python3-picamera2 \
    v4l-utils \
    git \
    libcamera-apps

# ── 2. Camera overlay (IMX519) ────────────────────────────────
CONFIG_FILE="/boot/firmware/config.txt"
[ -f "$CONFIG_FILE" ] || CONFIG_FILE="/boot/config.txt"

if ! grep -q "imx519" "$CONFIG_FILE"; then
    echo "[2/5] Adding IMX519 camera overlay to $CONFIG_FILE..."
    echo "" | sudo tee -a "$CONFIG_FILE"
    echo "# IMX519 autofocus camera" | sudo tee -a "$CONFIG_FILE"
    echo "dtoverlay=imx519" | sudo tee -a "$CONFIG_FILE"
    echo "camera_auto_detect=0" | sudo tee -a "$CONFIG_FILE"
    echo "  → Overlay added. A REBOOT is required after setup."
else
    echo "[2/5] IMX519 overlay already in $CONFIG_FILE — skipping."
fi

# ── 3. Python dependencies ────────────────────────────────────
echo "[3/5] Installing Python packages..."
pip3 install --break-system-packages -r "$POCKETSCAN_DIR/requirements.txt"

# ── 4. Photos directory ───────────────────────────────────────
echo "[4/5] Creating photos directory..."
mkdir -p "$POCKETSCAN_DIR/photos"

# ── 5. systemd service ────────────────────────────────────────
SERVICE_SRC="$POCKETSCAN_DIR/systemd/pocketscan.service"
SERVICE_DEST="/etc/systemd/system/pocketscan.service"

# Detect the real username (works with or without sudo)
REAL_USER="${SUDO_USER:-$(whoami)}"

echo "[5/5] Installing systemd service for user: $REAL_USER ..."
sed \
    -e "s|__POCKETSCAN_DIR__|$POCKETSCAN_DIR|g" \
    -e "s|__USER__|$REAL_USER|g" \
    "$SERVICE_SRC" | sudo tee "$SERVICE_DEST" > /dev/null

sudo systemctl daemon-reload
sudo systemctl enable pocketscan

echo ""
echo "========================================================"
echo "  Installation complete!"
echo ""
echo "  Next steps:"
echo "  1. Run the setup wizard:"
echo "       python3 $POCKETSCAN_DIR/scripts/setup.py"
echo ""
echo "  2. Reboot the Pi (for camera overlay):"
echo "       sudo reboot"
echo ""
echo "  3. Start the bot:"
echo "       sudo systemctl start pocketscan"
echo "       sudo journalctl -u pocketscan -f"
echo "========================================================"
echo ""
