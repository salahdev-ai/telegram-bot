"""
handlers.py -- Telegram bot command and button handlers for PocketScan.
"""
import asyncio
import logging
from functools import wraps
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot import camera, config

logger = logging.getLogger(__name__)

# ─── Security decorator ───────────────────────────────────────────────────────

def admin_only(func):
    """Silently ignore requests from any user that is not the admin."""
    @wraps(func)
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        uid = (update.effective_user or update.callback_query.from_user).id
        if uid != config.ADMIN_ID:
            logger.warning(f"Unauthorized access attempt from user_id={uid}")
            return
        return await func(update, ctx)
    return wrapper


# ─── Keyboard layout ─────────────────────────────────────────────────────────

def _main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📸  Take Photo", callback_data="take_photo")],
        # More buttons added here in future phases
    ])


# ─── /start ──────────────────────────────────────────────────────────────────

@admin_only
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    name = update.effective_user.first_name or "there"
    await update.message.reply_text(
        f"👋 *Hey {name}!*\n\n"
        "Welcome to *PocketScan* — your pocket document scanner.\n\n"
        "Point the camera at an A4 document and press the button below.\n"
        "The bot will auto-focus and send you a full-quality photo.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_main_keyboard(),
    )


# ─── Inline button callbacks ──────────────────────────────────────────────────

@admin_only
async def btn_take_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()                             # remove Telegram loading spinner

    # Immediate feedback
    status_msg = await query.message.reply_text(
        "⏳ *Focusing & capturing…*\n"
        "_Please hold the camera still_",
        parse_mode=ParseMode.MARKDOWN,
    )

    try:
        # Run blocking camera capture in a thread so the bot stays responsive
        loop = asyncio.get_event_loop()
        photo_path = await loop.run_in_executor(
            None,
            camera.capture_photo,
            config.PHOTO_DIR,
        )

        # Delete the "waiting" message and send the photo
        await status_msg.delete()
        with open(photo_path, "rb") as f:
            await query.message.reply_document(
                document=InputFile(f, filename=Path(photo_path).name),
                caption=(
                    "✅ *Scan complete!*\n"
                    f"📁 `{Path(photo_path).name}`\n"
                    f"📐 4656 × 3496 px  |  JPEG 95"
                ),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=_main_keyboard(),   # show buttons again
            )
        logger.info(f"Photo sent to user {query.from_user.id}: {photo_path}")

    except RuntimeError as exc:
        await status_msg.edit_text(
            f"❌ *Camera error*\n\n`{exc}`\n\nCheck the camera ribbon and drivers.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_main_keyboard(),
        )
        logger.error(f"Capture failed: {exc}")

    except Exception as exc:
        await status_msg.edit_text(
            f"❌ *Unexpected error*\n\n`{exc}`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_main_keyboard(),
        )
        logger.exception("Unexpected error during capture")
