# 📷 PocketScan — Raspberry Pi Telegram Document Scanner

Control your **16MP IMX519 autofocus camera** from Telegram.
Built for **Raspberry Pi Zero 2 W** running Raspberry Pi OS Bookworm.

---

## Hardware
| Component | Details |
|---|---|
| SBC | Raspberry Pi Zero 2 W |
| Camera | IMX519 16MP Autofocus (V4L2 / libcamera) |
| Resolution | 4656 × 3496 px (16 MP) |
| Focus range | 10 cm → ∞ |

---

## Quick Start (on the Pi)

```bash
# 1. Clone the repo
git clone https://github.com/youruser/pocketscan.git ~/pocketscan
cd ~/pocketscan

# 2. Run the install script
bash scripts/install.sh

# 3. Configure bot token + admin ID
python3 scripts/setup.py

# 4. Reboot (for camera overlay to load)
sudo reboot

# 5. Start the service
sudo systemctl start pocketscan
sudo journalctl -u pocketscan -f
```

---

## Deploy updates (from Windows PC)

```bash
# On Windows:
git add .
git commit -m "update"
git push origin main

# On Pi (SSH in):
cd ~/pocketscan
git pull origin main
sudo systemctl restart pocketscan
```

---

## Project Structure

```
pocketscan/
├── bot/
│   ├── config.py       # Loads .env settings
│   ├── camera.py       # IMX519 capture (picamera2 + V4L2 fallback)
│   ├── handlers.py     # Telegram commands & button callbacks
│   └── main.py         # Bot entry point
├── scripts/
│   ├── setup.py        # Interactive first-run wizard
│   └── install.sh      # One-shot Pi setup script
├── systemd/
│   └── pocketscan.service
├── photos/             # Captured scans (gitignored)
├── .env.example
├── requirements.txt
└── README.md
```

---

## Troubleshooting

```bash
# Check camera is detected
libcamera-hello --list-cameras

# Or with V4L2
v4l2-ctl --list-devices

# View bot logs
sudo journalctl -u pocketscan -f --no-pager
```
