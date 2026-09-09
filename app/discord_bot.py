import logging

import discord

from .config import Settings
from .grok_client import GrokClient
from .memory import ConversationMemory

log = logging.getLogger("grok-bot.discord")


class GrokDiscordClient(discord.Client):
    def __init__(
        self,
        settings: Settings,
        grok: GrokClient,
        memory: ConversationMemory,
        **kwargs,
    ) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents, **kwargs)
        self.settings = settings
        self.grok = grok
        self.memory = memory

    async def on_ready(self) -> None:
        log.info("Discord connected as %s", self.user)

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        is_dm = message.guild is None
        mentioned = self.user is not None and self.user in message.mentions
        channel_ok = (
            not self.settings.discord_channels
            or message.channel.id in self.settings.discord_channels
        )

        if not is_dm and not mentioned:
            return
        if not is_dm and not channel_ok:
            return

        text = message.content
        if self.user:
            text = text.replace(f"<@{self.user.id}>", "").replace(
                f"<@!{self.user.id}>", ""
            )
        text = text.strip()
        if not text:
            return

        chat_id = f"dc:{message.channel.id}:{message.author.id}"
        async with message.channel.typing():
            try:
                reply = self.grok.chat(self.memory.get(chat_id), text)
            except Exception:
                log.exception("Grok API call failed")
                await message.reply("Grok API call failed. Check VPS logs.")
                return

        self.memory.append(chat_id, "user", text)
        self.memory.append(chat_id, "assistant", reply)

        for i in range(0, max(len(reply), 1), 1900):
            await message.reply(reply[i : i + 1900] or "(empty reply)")
