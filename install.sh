#!/usr/bin/env bash
# One-command install for Grok VPS Bot.
# Usage on a fresh VPS:
#   curl -fsSL https://raw.githubusercontent.com/kylebailey9/grok-vps-bot/main/install.sh | bash
# Or with keys already set (no prompts):
#   XAI_API_KEY=xai-... TELEGRAM_BOT_TOKEN=... bash install.sh
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/kylebailey9/grok-vps-bot.git}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/grok-vps-bot}"
BRANCH="${BRANCH:-main}"

need_cmd() { command -v "$1" >/dev/null 2>&1; }

ask() {
  local var="$1" msg="$2" def="${3:-}"
  if [[ -n "${!var:-}" ]]; then
    return
  fi
  local answer=""
  if [[ -r /dev/tty ]]; then
    if [[ -n "$def" ]]; then
      read -r -p "$msg [$def]: " answer </dev/tty || true
      answer="${answer:-$def}"
    else
      read -r -p "$msg: " answer </dev/tty || true
    fi
  fi
  printf -v "$var" '%s' "$answer"
  export "$var"
}

info() { printf '\n\033[1;32m==>\033[0m %s\n' "$*"; }
die() { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

if [[ "$(id -u)" -eq 0 ]]; then
  SUDO=""
else
  SUDO="sudo"
fi

info "Installing Docker if needed"
if ! need_cmd docker; then
  if need_cmd apt-get; then
    $SUDO apt-get update -y
    $SUDO apt-get install -y ca-certificates curl git
    $SUDO apt-get install -y docker.io docker-compose-v2 || $SUDO apt-get install -y docker.io docker-compose
  elif need_cmd dnf; then
    $SUDO dnf install -y docker git
    $SUDO systemctl enable --now docker
  else
    die "Install Docker yourself, then re-run this script"
  fi
  $SUDO systemctl enable --now docker 2>/dev/null || true
fi

if [[ -n "${SUDO}" ]] && ! groups | grep -qw docker; then
  $SUDO usermod -aG docker "$USER" || true
  info "Added $USER to docker group (new SSH session needed for rootless docker)"
fi

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  elif need_cmd docker-compose; then
    docker-compose "$@"
  elif [[ -n "$SUDO" ]]; then
    $SUDO docker compose "$@"
  else
    die "docker compose plugin not found"
  fi
}

if ! docker info >/dev/null 2>&1; then
  if [[ -n "$SUDO" ]]; then
    compose() { $SUDO docker compose "$@"; }
    if ! $SUDO docker info >/dev/null 2>&1; then
      die "Docker is installed but not running. Try: sudo systemctl start docker"
    fi
  fi
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-}")" 2>/dev/null && pwd || true)"
if [[ -f "${SCRIPT_DIR:-}/docker-compose.yml" && -f "${SCRIPT_DIR:-}/app/main.py" ]]; then
  INSTALL_DIR="$SCRIPT_DIR"
  info "Using existing project at $INSTALL_DIR"
else
  info "Fetching project into $INSTALL_DIR"
  if need_cmd apt-get; then
    $SUDO apt-get install -y git >/dev/null 2>&1 || true
  fi
  if [[ -d "$INSTALL_DIR/.git" ]]; then
    git -C "$INSTALL_DIR" fetch --depth 1 origin "$BRANCH"
    git -C "$INSTALL_DIR" checkout "$BRANCH"
    git -C "$INSTALL_DIR" pull --ff-only origin "$BRANCH" || true
  elif [[ -d "$INSTALL_DIR" && -f "$INSTALL_DIR/docker-compose.yml" ]]; then
    true
  else
    mkdir -p "$(dirname "$INSTALL_DIR")"
    git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
  fi
fi

cd "$INSTALL_DIR"

ask XAI_API_KEY "xAI API key (console.x.ai)"
[[ -n "${XAI_API_KEY:-}" ]] || die "XAI_API_KEY is required. Export it and re-run."

ask TELEGRAM_BOT_TOKEN "Telegram bot token from @BotFather (blank to skip)"
ask DISCORD_BOT_TOKEN "Discord bot token (blank to skip)"
ask WEB_ACCESS_KEY "Web UI access key" "$(head -c 18 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 24)"
ask GROK_MODEL "Grok model" "grok-4.6"
ask TELEGRAM_ALLOWED_USER_IDS "Telegram allowlist user ids, comma-separated (blank = anyone)"

if [[ -z "${TELEGRAM_BOT_TOKEN:-}" && -z "${DISCORD_BOT_TOKEN:-}" ]]; then
  info "No chat tokens set — web UI only on port 8080"
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

set_env() {
  local key="$1" val="$2"
  python3 - "$key" "$val" <<'PY'
import pathlib, sys
key, val = sys.argv[1], sys.argv[2]
path = pathlib.Path(".env")
text = path.read_text() if path.exists() else ""
lines = text.splitlines()
found = False
out = []
for line in lines:
    if line.startswith(key + "="):
        out.append(f"{key}={val}")
        found = True
    else:
        out.append(line)
if not found:
    out.append(f"{key}={val}")
path.write_text("\n".join(out) + "\n")
PY
}

set_env XAI_API_KEY "$XAI_API_KEY"
set_env GROK_MODEL "${GROK_MODEL:-grok-4.6}"
set_env TELEGRAM_BOT_TOKEN "${TELEGRAM_BOT_TOKEN:-}"
set_env DISCORD_BOT_TOKEN "${DISCORD_BOT_TOKEN:-}"
set_env WEB_ACCESS_KEY "${WEB_ACCESS_KEY:-change-me}"
set_env TELEGRAM_ALLOWED_USER_IDS "${TELEGRAM_ALLOWED_USER_IDS:-}"
set_env WEB_ENABLED "true"

info "Building and starting the bot"
compose up -d --build

IP="$(curl -4 -fsS ifconfig.me 2>/dev/null || curl -4 -fsS icanhazip.com 2>/dev/null || echo YOUR_VPS_IP)"

cat <<EOF

Grok bot is up.

  folder : $INSTALL_DIR
  web UI : http://$IP:8080
  key    : ${WEB_ACCESS_KEY}
  model  : ${GROK_MODEL:-grok-4.6}

Telegram: open the bot and send /start then /whoami
Logs:     cd $INSTALL_DIR && docker compose logs -f
Stop:     cd $INSTALL_DIR && docker compose down

EOF
