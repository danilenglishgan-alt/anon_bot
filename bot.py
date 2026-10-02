import asyncio
import logging
import os
import html
import sqlite3
from datetime import datetime, timezone

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

TOKEN = os.environ["BOT_TOKEN"]
OWNER_ID = int(os.environ["OWNER_ID"])
DB_PATH = os.environ.get("DB_PATH", "anon.db")

db = sqlite3.connect(DB_PATH)
db.executescript(
    """
    -- какое сообщение у владельца от какого отправителя (нужно для ответов)
    CREATE TABLE IF NOT EXISTS routes (
        message_id INTEGER PRIMARY KEY,
        sender_id INTEGER NOT NULL
    );
    -- журнал всех входящих сообщений (для жалоб и обращений в правоохранительные органы)
    CREATE TABLE IF NOT EXISTS log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        owner_message_id INTEGER,
        sender_id INTEGER NOT NULL,
        username TEXT,
        full_name TEXT,
        content_type TEXT NOT NULL,
        text TEXT,
        file_id TEXT
    );
    CREATE TABLE IF NOT EXISTS blocks (
        sender_id INTEGER PRIMARY KEY
    );
    """
)

bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

WELCOME = (
    "🚀 Здесь можно отправить <b>анонимное сообщение</b> человеку, "
    "который опубликовал эту ссылку.\n\n"
    "⚡️ <b>Напишите сюда всё, что хотите ему передать,</b> и через несколько секунд "
    "он получит ваше сообщение, но не будет знать от кого.\n\n"
    "<blockquote>Отправить можно: текст, фото, видео, стикеры, "
    "голосовые и видеосообщения (кружки)</blockquote>\n\n"
    "<i>Сообщения сохраняются. При нарушении закона данные могут быть "
    "переданы правоохранительным органам.</i>"
)
SENT = "✅ <b>Сообщение отправлено, ожидайте ответ!</b>"

owner = F.from_user.id == OWNER_ID


def file_id_of(m: Message) -> str | None:
    if m.photo:
        return m.photo[-1].file_id
    for attr in ("video", "voice", "video_note", "audio", "document", "sticker", "animation"):
        obj = getattr(m, attr, None)
        if obj:
            return obj.file_id
    return None


@dp.message(owner, CommandStart())
async def owner_start(message: Message):
    username = (await bot.get_me()).username
    await message.answer(
        "👋 Бот работает. Все анонимные сообщения будут приходить сюда.\n\n"
        f"Твоя ссылка для публикации:\nhttps://t.me/{username}\n\n"
        "Чтобы ответить автору — сделай «Ответить» на его сообщение.\n"
        "Чтобы заблокировать автора — ответь на его сообщение командой /block.\n"
        "Чтобы узнать данные автора (для жалоб) — ответь командой /who.\n"
        "Полный журнал: таблица log в базе data/anon.db."
    )


@dp.message(owner, Command("block"))
async def owner_block(message: Message):
    reply = message.reply_to_message
    row = reply and db.execute(
        "SELECT sender_id FROM routes WHERE message_id=?", (reply.message_id,)
    ).fetchone()
    if not row:
        await message.answer("Ответь этой командой на сообщение автора, которого нужно заблокировать.")
        return
    db.execute("INSERT OR IGNORE INTO blocks VALUES (?)", (row[0],))
    db.commit()
    await message.answer("🚫 Автор заблокирован.")


@dp.message(owner, Command("who"))
async def owner_who(message: Message):
    """Ответом на сообщение — показать данные отправителя из журнала."""
    reply = message.reply_to_message
    row = reply and db.execute(
        "SELECT ts, sender_id, username, full_name, content_type FROM log "
        "WHERE owner_message_id=? ORDER BY id DESC LIMIT 1",
        (reply.message_id,),
    ).fetchone()
    if not row:
        await message.answer("Ответь этой командой на анонимное сообщение.")
        return
    ts, sid, username, name, ctype = row
    await message.answer(
        f"🔎 <b>Отправитель</b>\nID: <code>{sid}</code>\n"
        f"Имя: {html.escape(name or '—')}\nUsername: {'@' + html.escape(username) if username else '—'}\n"
        f"Тип: {ctype}\nВремя (UTC): {ts}",
    )


@dp.message(owner)
async def owner_reply(message: Message):
    """Владелец отвечает на анонимное сообщение -> уходит автору."""
    reply = message.reply_to_message
    row = reply and db.execute(
        "SELECT sender_id FROM routes WHERE message_id=?", (reply.message_id,)
    ).fetchone()
    if not row:
        await message.answer("Чтобы ответить, сделай «Ответить» на анонимное сообщение.")
        return
    await bot.send_message(row[0], "💬 <b>Вам ответили на анонимное сообщение:</b>")
    await message.copy_to(row[0])
    await message.answer("✅ Ответ отправлен.")


@dp.message(CommandStart())
async def sender_start(message: Message):
    await message.answer(WELCOME)


@dp.message()
async def sender_message(message: Message):
    uid = message.from_user.id
    if not db.execute("SELECT 1 FROM blocks WHERE sender_id=?", (uid,)).fetchone():
        header = await bot.send_message(OWNER_ID, "📨 <b>Новое анонимное сообщение:</b>")
        copied = await message.copy_to(OWNER_ID)
        db.executemany(
            "INSERT OR REPLACE INTO routes VALUES (?, ?)",
            [(header.message_id, uid), (copied.message_id, uid)],
        )
        u = message.from_user
        db.execute(
            "INSERT INTO log (ts, owner_message_id, sender_id, username, full_name, "
            "content_type, text, file_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                copied.message_id, uid, u.username, u.full_name,
                message.content_type, message.text or message.caption, file_id_of(message),
            ),
        )
        db.commit()
    # заблокированный автор не должен об этом знать
    await message.reply(SENT)


async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
