import asyncio, logging, os
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Dict, Set

import pytz
import aiosqlite

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode, ChatType
from aiogram.client.default import DefaultBotProperties

# ── ENV ────────────────────────────────────────────────────────────────────────
TOKEN: str = os.getenv("BOT_TOKEN", "")
GROUP_ID: int = int(os.getenv("GROUP_ID", "0"))
TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Yekaterinburg")   # Челябинск
ROSTER_RAW: str = os.getenv("ROSTER_USERNAMES", "")           # "user1,user2", без @

if not TOKEN or not GROUP_ID:
    raise SystemExit("Set BOT_TOKEN and GROUP_ID environment variables.")

TZ = pytz.timezone(TIMEZONE)

def _parse_roster(raw: str) -> Set[str]:
    items = [x.strip().lstrip("@").lower() for x in raw.split(",")]
    return {x for x in items if x}

ROSTER: Set[str] = _parse_roster(ROSTER_RAW)

# ── BOT / DP ───────────────────────────────────────────────────────────────────
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp  = Dispatcher()

# ── DB ─────────────────────────────────────────────────────────────────────────
DB_PATH = "quran.sqlite3"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            user_id      INTEGER PRIMARY KEY,
            first_name   TEXT,
            username     TEXT,
            private_chat INTEGER DEFAULT 0,  -- /start в ЛС (сейчас не используем)
            is_active    INTEGER DEFAULT 1
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
    """Кликабельное упоминание: @username если есть, иначе tg:// по id."""
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

async def get_participants(active_only=True) -> List[Tuple[int,str,Optional[str],int,int]]:
    q = "SELECT user_id, first_name, username, private_chat, is_active FROM participants"
    if active_only:
        q += " WHERE is_active=1"
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(q) as cur:
            return await cur.fetchall()

async def get_username_map() -> Dict[str, Tuple[int,str,Optional[str],int,int]]:
    """username(lower) -> (user_id, first_name, username, private_chat, is_active)"""
    rows = await get_participants(active_only=False)
    out: Dict[str, Tuple[int,str,Optional[str],int,int]] = {}
    for u, fn, un, pm, act in rows:
        if un:
            out[un.lower()] = (u, fn, un, pm, act)
    return out

async def get_reported_usernames_for(date: str) -> Set[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
        SELECT p.username
        FROM reports r
        JOIN participants p ON p.user_id = r.user_id
        WHERE r.date=? AND p.username IS NOT NULL
        """, (date,)) as cur:
            rows = await cur.fetchall()
    return {un.lower() for (un,) in rows if un}

# ── HANDLERS ───────────────────────────────────────────────────────────────────
@dp.message(F.chat.id == GROUP_ID)
async def track_participants(message: types.Message):
    """Любое сообщение в группе — запоминаем участника (чтобы упоминать кликабельно)."""
    if message.from_user:
        await ensure_participant(message.from_user)

@dp.message(F.chat.id == GROUP_ID, F.photo)
async def mark_report(message: types.Message):
    """Фото в группе = отчёт за сегодня."""
    if message.from_user:
        await ensure_participant(message.from_user)
        await add_report(message.from_user.id, today_str())
        name = message.from_user.full_name or message.from_user.first_name or "друг"
        await message.reply(f"МашаАллах, {name}! Аллах примет")

@dp.message(F.chat.id == GROUP_ID, F.text == "/missed")
async def cmd_missed(message: types.Message):
    """Быстрая проверка, кого нет сегодня (только по БД участников/отчётов)."""
    rows = await get_participants(active_only=True)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM reports WHERE date=?", (today_str(),)) as cur:
            reported_ids = {r[0] for r in await cur.fetchall()}
    missed = [r for r in rows if r[0] not in reported_ids]
    if not missed:
        return await message.reply("Сегодня все отметились. МашаАллах!")
    lst = ", ".join([mention(u, fn, un) for (u, fn, un, _, _) in missed])
    await message.reply(f"Сегодня ещё нет отчёта: {lst}")

# ── MOTIVATION (30 фраз) ───────────────────────────────────────────────────────
AYAT_ROTATION = [
    "Читайте Коран, братья, ибо он придёт заступником в Судный день для своих обладателей.",
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
    day = int(datetime.now(TZ).strftime("%d"))  # 1..31
    return AYAT_ROTATION[(day - 1) % len(AYAT_ROTATION)]

# ── DAILY REMINDER @ 23:00 ─────────────────────────────────────────────────────
async def send_daily_reminders():
    roster = set(ROSTER)                              # usernames (lower)
    uname_map = await get_username_map()              # username -> profile
    reported_unames = await get_reported_usernames_for(today_str())

    # если ростер пуст — берём всех активных, кто писал когда‑либо
    if not roster:
        parts = await get_participants(active_only=True)
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT user_id FROM reports WHERE date=?", (today_str(),)) as cur:
                reported_ids = {r[0] for r in await cur.fetchall()}
        missed_rows = [p for p in parts if p[0] not in reported_ids]
        if not missed_rows:
            try: await bot.send_message(GROUP_ID, "Сегодня все отметились. МашаАллах!")
            except Exception: pass
        else:
            lst = ", ".join([mention(u, fn, un) for (u, fn, un, _, _) in missed_rows])
            head = daily_headline()
            try: await bot.send_message(GROUP_ID, f"{head}\nСегодня ещё не отметились: {lst}")
            except Exception: pass
        # чистим старые отчёты
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM reports WHERE date < ?", (today_str(),))
            await db.commit()
        return

    # есть фиксированный список username
    missed_unames = sorted(roster - reported_unames)
    if not missed_unames:
        try: await bot.send_message(GROUP_ID, "Сегодня все из списка отметились. МашаАллах!")
        except Exception: pass
    else:
        head = daily_headline()
        tags = []
        for uname in missed_unames:
            profile = uname_map.get(uname)
            if profile:
                user_id, first_name, username, _, _ = profile
                tags.append(mention(user_id, first_name, username))
            else:
                tags.append(f"@{uname}")  # молчун с username, ещё не писал в группе
        text = f"{head}\nСегодня ещё не отметились: " + ", ".join(tags)
        try: await bot.send_message(GROUP_ID, text)
        except Exception: pass

    # чистим старые отчёты
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM reports WHERE date < ?", (today_str(),))
        await db.commit()

async def scheduler_23_00():
    """Триггер каждый день в 23:00 (Челябинск)."""
    while True:
        now = datetime.now(TZ)
        target = now.replace(hour=23, minute=0, second=0, microsecond=0)
        if target <= now:
            target = target + timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())
        try:
            await send_daily_reminders()
        except Exception as e:
            logging.exception(f"Daily reminder error: {e}")

# ── MAIN ───────────────────────────────────────────────────────────────────────
async def main():
    logging.basicConfig(level=logging.INFO)
    await init_db()

    # критично: выключаем webhook, чтобы точно не было конфликта
    await bot.delete_webhook(drop_pending_updates=True)

    # фоновые задачи
    asyncio.create_task(scheduler_23_00())

    # запускаем polling (единственный способ получения апдейтов)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
