import asyncio
import logging
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

load_dotenv()

from app.config import get_settings
from app.grok_client import GrokClient
from app.memory import ConversationMemory
from app.telegram_bot import build_telegram_app
from app.web_server import build_web_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("grok-bot")


async def run() -> None:
    settings = get_settings()
    grok = GrokClient(settings)
    memory = ConversationMemory(max_turns=settings.max_history_turns)

    tasks = []

    if settings.web_enabled:
        web = build_web_app(settings, grok, memory)
        config = uvicorn.Config(
            web,
            host=settings.web_host,
            port=settings.web_port,
            log_level="info",
        )
        server = uvicorn.Server(config)
        tasks.append(asyncio.create_task(server.serve(), name="web"))
        log.info("Web chat on http://%s:%s", settings.web_host, settings.web_port)

    if settings.telegram_bot_token:
        tg = build_telegram_app(settings, grok, memory)
        await tg.initialize()
        await tg.start()
        await tg.updater.start_polling(drop_pending_updates=True)
        log.info("Telegram polling started")
    else:
        log.warning("TELEGRAM_BOT_TOKEN empty — Telegram disabled")

    if settings.discord_bot_token:
        from app.discord_bot import GrokDiscordClient

        dc = GrokDiscordClient(settings, grok, memory)
        tasks.append(asyncio.create_task(dc.start(settings.discord_bot_token), name="discord"))
        log.info("Discord starting")
    else:
        log.warning("DISCORD_BOT_TOKEN empty — Discord disabled")

    if not settings.telegram_bot_token and not settings.discord_bot_token and not settings.web_enabled:
        raise SystemExit("Enable at least one channel: Telegram, Discord, or web.")

    if not tasks and settings.telegram_bot_token:
        stop = asyncio.Event()
        try:
            await stop.wait()
        except asyncio.CancelledError:
            pass
        return

    if tasks:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
        for t in pending:
            t.cancel()
        for t in done:
            if t.exception():
                raise t.exception()


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        log.info("Shutting down")


if __name__ == "__main__":
    main()
