# quran_bot.py
import asyncio
import logging
import os
from datetime import datetime, timedelta, time

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message

# ── Логирование ─────────────────────────────────
logging.basicConfig(level=logging.INFO)

# ── Конфиг ──────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")                 # токен бота
GROUP_ID  = int(os.getenv("GROUP_ID", "0"))        # id группы (со знаком -100...)
TIMEZONE_OFFSET = int(os.getenv("TZ_OFFSET", "5")) # смещение от UTC, напр. Челябинск = +5

if not BOT_TOKEN or GROUP_ID == 0:
    raise RuntimeError("Нужно задать BOT_TOKEN и GROUP_ID в переменных окружения.")

bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher()

# ── Реакция только на фото в нужной группе ─────
@dp.message(F.chat.id == GROUP_ID, F.photo)
async def handle_photo(message: Message):
    # построчно, как просил
    await message.answer("بارك الله فيك")
    await message.answer("Пусть Аллаh примет,")
    await message.answer("آمين 🤲")

# ── 30 мотивашек (фиксированный порядок, по одной в день) ──
MOTIVATIONS = [
    "Сегодня не все отметились. Давайте завтра будем активнее, ин ша Аллах!",
    "Не забывайте про чтение Корана — это свет в сердце.",
    "Аллах любит тех, кто старается ради Него.",
    "Кто держится за Коран — тот никогда не заблудится.",
    "Каждый день с Кораном — приближение к Раю.",
    "Пусть завтра будет больше барракята в наших стараниях.",
    "Давайте вместе укрепим нашу связь с Книгой Аллаха.",
    "«Воистину, этим Кораном направляет Он, кого пожелает» (39:23).",
    "С каждым аятом приближаемся к довольству Аллаха.",
    "Завтра — ещё один шанс проявить усердие.",
    "Коран — лучший друг и помощник в этом мире и в Ахира.",
    "Кто читает Коран — наполняет сердце светом.",
    "Аллах возвышает людей через Коран.",
    "Усердие сегодня — награда в Судный день.",
    "Слово Аллаха — лекарство для душ и сердец.",
    "Не упускай возможность приблизиться к Аллаху через чтение.",
    "Коран ведёт к счастью и спокойствию.",
    "Пусть наши сердца будут мягкими благодаря Корану.",
    "Аллах облегчит путь в Рай тем, кто учит Коран.",
    "Каждое прочитанное слово — это награда.",
    "Пусть Коран будет нашим заступником в Судный день.",
    "Нет усталости, когда рядом Коран.",
    "Аллах открывает пути тем, кто держится за Его Книгу.",
    "Слова Аллаха сильнее любых трудностей.",
    "Коран укрепляет иман и приносит спокойствие.",
    "Каждый аят — обращение Всевышнего к тебе.",
    "Аллах любит тех, кто очищает сердце Кораном.",
    "Не позволяй дню пройти без аятов Корана.",
    "Коран — источник силы и терпения.",
    "В каждом дне найди минуту для Корана — и увидишь барракат.",
]

def local_now() -> datetime:
    """Текущее время по твоему смещению (UTC+OFFSET)."""
    return datetime.utcnow() + timedelta(hours=TIMEZONE_OFFSET)

def next_time(hour: int, minute: int = 0) -> datetime:
    """Ближайшее локальное время H:M от текущего момента."""
    now = local_now()
    target = datetime.combine(now.date(), time(hour, minute))
    if now >= target:
        target += timedelta(days=1)
    return target

def rotation_index_for_day(d: datetime) -> int:
    """Индекс мотивашки: стабильный по дню, идём по порядку, потом цикл."""
    return (d.date().toordinal()) % len(MOTIVATIONS)

async def daily_motivation_loop():
    """Каждый день в 22:00 по локальному смещению отправляем мотивашку №i."""
    while True:
        target = next_time(22, 0)  # 22:00 локально
        sleep_sec = (target - local_now()).total_seconds()
        await asyncio.sleep(max(0, sleep_sec))

        idx = rotation_index_for_day(target)
        text = MOTIVATIONS[idx]
        try:
            await bot.send_message(GROUP_ID, text)
        except Exception as e:
            logging.error(f"Не удалось отправить мотивашку: {e}")

# ── Запуск ─────────────────────────────────────
async def main():
    # Планировщик мотивашек
    asyncio.create_task(daily_motivation_loop())
    # Старт поллинга
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
