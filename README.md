# Бот анонимных сообщений

Бот личный: все сообщения приходят только владельцу (`OWNER_ID`). Любой, кто открыл бота, пишет
анонимно, а владелец видит только текст/медиа. Владелец может ответить (Reply) — ответ уйдёт автору, тоже анонимно.
`/block` (ответом на сообщение) блокирует автора.

## Установка на сервер (одной командой)
Нужен любой Linux-сервер (VPS) с root-доступом:

    git clone https://github.com/danilenglishgan-alt/anon_bot.git && cd anon_bot && BOT_TOKEN=ТОКЕН OWNER_ID=ТВОЙ_ID bash install.sh

Скрипт сам поставит Docker, соберёт и запустит бота (перезапускается сам после перезагрузки сервера).
База хранится в `./data`. Логи: `docker compose logs -f`. Обновить: `git pull && docker compose up -d --build`.

## Локальный запуск
    pip install -r requirements.txt
    export BOT_TOKEN=... OWNER_ID=... && python bot.py

## Журнал сообщений
Все входящие сообщения пишутся в таблицу `log` (время UTC, ID, имя, username, тип, текст/подпись, file_id медиа).
- В боте: ответь командой `/who` на анонимное сообщение — покажет данные отправителя.
- На сервере: `sqlite3 data/anon.db "SELECT ts, sender_id, username, content_type, text FROM log ORDER BY id DESC LIMIT 20;"`
- Бэкап: копируй `data/anon.db`. Доступ к серверу и базе — только у владельца.
