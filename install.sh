#!/usr/bin/env bash
# Установка и запуск бота одной командой:
#   BOT_TOKEN=123:abc OWNER_ID=123456789 bash install.sh
# (или просто `bash install.sh` — спросит сам)
# OWNER_ID — твой числовой Telegram ID (узнать: бот @userinfobot)
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f .env ]; then
  if [ -z "${BOT_TOKEN:-}" ]; then
    read -rsp "Токен бота от @BotFather: " BOT_TOKEN; echo
  fi
  if [ -z "${OWNER_ID:-}" ]; then
    read -rp "Твой Telegram ID (число, из @userinfobot): " OWNER_ID
  fi
  (umask 077; printf 'BOT_TOKEN=%s\nOWNER_ID=%s\n' "$BOT_TOKEN" "$OWNER_ID" > .env)
fi

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi

mkdir -p data
docker compose up -d --build
echo "Готово. Логи: docker compose logs -f"
