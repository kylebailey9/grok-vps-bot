import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .config import Settings
from .grok_client import GrokClient
from .memory import ConversationMemory

log = logging.getLogger("grok-bot.telegram")


def build_telegram_app(
    settings: Settings, grok: GrokClient, memory: ConversationMemory
) -> Application:
    app = Application.builder().token(settings.telegram_bot_token).build()

    def allowed(user_id: int | None) -> bool:
        if not settings.telegram_allowlist:
            return True
        return user_id is not None and user_id in settings.telegram_allowlist

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not allowed(update.effective_user.id if update.effective_user else None):
            return
        await update.message.reply_text(
            f"Hey. I'm Grok on your VPS ({settings.grok_model}).\n"
            "Just send a message. /reset clears this chat. /whoami shows your id."
        )

    async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not allowed(update.effective_user.id if update.effective_user else None):
            return
        await update.message.reply_text(
            "/start — intro\n"
            "/reset — clear conversation memory\n"
            "/whoami — your Telegram user id (for the allowlist)\n"
            "/model — current Grok model"
        )

    async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        uid = update.effective_user.id if update.effective_user else "?"
        await update.message.reply_text(f"Your Telegram user id: `{uid}`", parse_mode="Markdown")

    async def model_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not allowed(update.effective_user.id if update.effective_user else None):
            return
        await update.message.reply_text(f"Model: `{settings.grok_model}`", parse_mode="Markdown")

    async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not allowed(update.effective_user.id if update.effective_user else None):
            return
        memory.reset(f"tg:{update.effective_chat.id}")
        await update.message.reply_text("Memory wiped for this chat.")

    async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.message.text:
            return
        user = update.effective_user
        if not allowed(user.id if user else None):
            await update.message.reply_text("You're not on the allowlist.")
            return

        chat_id = f"tg:{update.effective_chat.id}"
        text = update.message.text.strip()
        if not text:
            return

        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, action=ChatAction.TYPING
        )
        try:
            history = memory.get(chat_id)
            reply = grok.chat(history, text)
        except Exception:
            log.exception("Grok API call failed")
            await update.message.reply_text(
                "Grok API call failed. Check XAI_API_KEY, credits, and VPS logs."
            )
            return

        memory.append(chat_id, "user", text)
        memory.append(chat_id, "assistant", reply)

        for i in range(0, max(len(reply), 1), 4000):
            chunk = reply[i : i + 4000] or "(empty reply)"
            await update.message.reply_text(chunk)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("whoami", whoami))
    app.add_handler(CommandHandler("model", model_cmd))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    return app
