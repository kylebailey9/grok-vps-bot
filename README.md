# Grok VPS Bot

Self-hosted Grok on **your** VPS. Official Grok Bot runs on xAI cloud and cannot be installed on your server. This is the practical replacement: Grok API + Telegram + Discord + a tiny web chat, in Docker.

## One command (fresh Ubuntu/Debian VPS)

```bash
XAI_API_KEY='xai-...' TELEGRAM_BOT_TOKEN='123:ABC' \
  bash -c 'curl -fsSL https://raw.githubusercontent.com/kylebailey9/grok-vps-bot/main/install.sh | bash'
```

That installs Docker if needed, clones this repo to `~/grok-vps-bot`, writes `.env`, and starts the bot.

Interactive (asks for keys over the terminal):

```bash
curl -fsSL https://raw.githubusercontent.com/kylebailey9/grok-vps-bot/main/install.sh | bash
```

Optional env vars: `DISCORD_BOT_TOKEN`, `GROK_MODEL`, `WEB_ACCESS_KEY`, `TELEGRAM_ALLOWED_USER_IDS`.

Repo: https://github.com/kylebailey9/grok-vps-bot
