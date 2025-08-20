import asyncio, logging, os
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Dict, Set

import pytz
import aiosqlite

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode, ChatType
from aiogram.client.default import DefaultBotProperties

# ── CONFIG ───────────────────────────────
TOKEN: str = os.getenv("BOT_TOKEN", "")
GROUP_ID: int = int(os.getenv("GROUP_ID", "0"))
TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Yekaterinburg")   # Челябинск
ROSTER_RAW: str = os.getenv("ROSTER_USERNAMES", "")           # "user1,user2,...", без @

if not TOKEN or not GROUP_ID:
    raise SystemExit("Set BOT_TOKEN and GROUP_ID environment variables.")

TZ = pytz.timezone(TIMEZONE)

def _parse_roster(raw: str) -> Set[str]:
    items = [x.strip().lstrip("@").lower() for x in raw.split(",")]
    return {x for x in items if x}

ROSTER: Set[str] = _parse_roster(ROSTER_RAW)

# ── BOT / DP ─────────────────────────────
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp  = Dispatcher()

# ── DB ───────────────────────────────────
DB_PATH = "quran.sqlite3"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            user_id      INTEGER PRIMARY KEY,
            first_name   TEXT,
            username     TEXT
        )""")
        await db.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            user_id INTEGER,
            date    TEXT,
            PRIMARY KEY (user_id, date)
        )""")
        await db.commit()

def today_str() -> str:
    return datetime.now(TZ).strftime("%Y-%m-%d")

def mention(user_id: int, first_name: Optional[str], username: Optional[str]) -> str:
    if username:
        return f"@{username}"
    safe = (first_name or "участник").replace("<","").replace(">","")
    return f'<a href="tg://user?id={user_id}">{safe}</a>'

async def ensure_participant(user: types.User):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO participants(user_id, first_name, username)
        VALUES(?,?,?)
        ON CONFLICT(user_id) DO UPDATE SET
          first_name=excluded.first_name,
          username=excluded.username
        """, (user.id, user.full_name or user.first_name or "", user.username))
        await db.commit()

async def add_report(user_id: int, date: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO reports(user_id, date) VALUES(?,?)", (user_id, date))
        await db.commit()

async def get_participants() -> List[Tuple[int,str,Optional[str]]]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, first_name, username FROM participants") as cur:
            return await cur.fetchall()

async def get_reported_ids_for(date: str) -> Set[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM reports WHERE date=?", (date,)) as cur:
            return {r[0] for r in await cur.fetchall()}

# ── HANDLERS ─────────────────────────────
@dp.message(F.chat.id == GROUP_ID)
async def track(message: types.Message):
    """Любое сообщение в группе → запоминаем участника."""
    if message.from_user:
        await ensure_participant(message.from_user)

@dp.message(F.chat.id == GROUP_ID, F.photo)
async def mark_report(message: types.Message):
    """Фото = отчёт за сегодня."""
    if message.from_user:
        await ensure_participant(message.from_user)
        await add_report(message.from_user.id, today_str())
        name = message.from_user.full_name or message.from_user.first_name or "брат"
        await message.reply(f"МашаАллах, {name}! Аллах примет 🤲")

# ── MOTIVATION ───────────────────────────
AYAT_ROTATION = [
    "Читайте Коран, братья, ибо он придёт заступником в Судный день.",
    "Лучшие из вас — те, кто изучает Коран и обучает ему.",
    "Поистине, в поминании Аллаха сердца находят успокоение (13:28).",
    "Коран — свет и руководство. Удели ему хотя бы десять страниц сегодня.",
    "Оживи сердце чтением Корана — пусть каждая страница будет доводом за тебя.",
    "Аллах любит постоянство в делах, даже если они малы.",
    "Не откладывай на завтра то, что приблизит тебя сегодня.",
    "Каждая страница — шаг к довольству Аллаха. Сделай свой шаг.",
    "Кто идёт по пути знания, тому Аллах облегчает путь в Рай (хадис).",
    "Пусть Коран будет твоим спутником до сна и после пробуждения.",
    "Коран — лекарство для сердец. Не оставляй его.",
    "В каждой букве Корана — десять благих дел. Умножай награду легко.",
    "Чтение Корана очищает душу так, как вода очищает тело.",
    "Коран — это твоя прямая связь с Аллахом. Не разрывай её.",
    "Каждое чтение — приближение к Раю и удаление от Огня.",
    "Тот, кто держится за Коран, никогда не собьётся с пути.",
    "Коран — верный друг, который не оставит в могиле.",
    "Украшай свои дни словами Аллаха.",
    "Коран — ключ к успеху в этом мире и в Ахира.",
    "О Аллах, сделай Коран весной наших сердец.",
    "Не упускай возможность, ведь каждая страница может стать твоей защитой.",
    "Поистине, Коран возвышает одних и унижает других.",
    "Не будь из тех, кто оставил Коран за спиной.",
    "Чтение Корана — лучшая привычка, с которой начинается и заканчивается день.",
    "Пусть твой голос украшается Кораном.",
    "Каждая страница Корана приближает к довольству Аллаха.",
    "Не позволяй шайтана лишать тебя чтения Корана.",
    "Поистине, Коран — верное руководство без сомнения.",
    "Кто изучает Коран в молодости, тот смешивает его с кровью и плотью.",
    "Будь из людей Корана — они особенные у Аллаха.",
]

def daily_headline() -> str:
    day = int(datetime.now(TZ).strftime("%d"))
    return AYAT_ROTATION[(day - 1) % len(AYAT_ROTATION)]

# ── DAILY REMINDER ───────────────────────
async def send_daily_reminder():
    participants = await get_participants()
    reported_ids = await get_reported_ids_for(today_str())

    missed = [p for p in participants if p[0] not in reported_ids]

    # добавляем молчунов из ROSTER
    missed_usernames = set(un.lower() for _, _, un in missed if un)
    roster_missed = [f"@{un}" for un in ROSTER if un not in missed_usernames]

    if not missed and not roster_missed:
        text = "Сегодня все отметились. МашаАллах!"
    else:
        tags = [mention(u, fn, un) for (u, fn, un) in missed]
        tags += roster_missed
        text = f"{daily_headline()}\nСегодня ещё не отметились: " + ", ".join(tags)

    try:
        await bot.send_message(GROUP_ID, text)
    except Exception as e:
        logging.error(f"Reminder send error: {e}")

async def scheduler_23_00():
    while True:
        now = datetime.now(TZ)
        target = now.replace(hour=23, minute=0, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())
        await send_daily_reminder()

# ── MAIN ─────────────────────────────────
async def main():
    logging.basicConfig(level=logging.INFO)
    await init_db()
    asyncio.create_task(scheduler_23_00())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
