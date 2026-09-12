"""
main.py -- PocketScan Bot entry point.
Run with:  python3 bot/main.py
Or via systemd service (see systemd/pocketscan.service).
"""
import logging
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
)

from bot import config
from bot.handlers import cmd_start, btn_take_photo, btn_check_camera

logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Starting PocketScan bot...")

    app = (
        Application.builder()
        .token(config.TOKEN)
        .build()
    )

    # ── Register handlers ─────────────────────────────────────
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(btn_take_photo,   pattern="^take_photo$"))
    app.add_handler(CallbackQueryHandler(btn_check_camera, pattern="^check_camera$"))

    # ── Start polling ─────────────────────────────────────────
    logger.info(f"Bot running | Admin ID: {config.ADMIN_ID} | Photos: {config.PHOTO_DIR}")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
