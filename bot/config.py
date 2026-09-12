"""config.py -- Loads and validates .env settings for PocketScan."""
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (parent of bot/)
_root = Path(__file__).resolve().parent.parent
load_dotenv(_root / ".env")


def _require(key: str) -> str:
    """Return env var or exit with a helpful message."""
    val = os.getenv(key, "").strip()
    if not val:
        print(f"\n[ERROR] Missing required config: {key}")
        print("  Run:  python3 scripts/setup.py  to configure the bot\n")
        sys.exit(1)
    return val


TOKEN: str      = _require("TELEGRAM_BOT_TOKEN")
ADMIN_ID: int   = int(_require("ADMIN_USER_ID"))
PHOTO_DIR: Path = Path(os.getenv("PHOTO_DIR", "/home/pi/pocketscan/photos"))
LOG_LEVEL: str  = os.getenv("LOG_LEVEL", "INFO").upper()

# Ensure photo directory exists
PHOTO_DIR.mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
