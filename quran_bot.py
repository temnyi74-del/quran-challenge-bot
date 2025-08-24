# quran_bot.py

import asyncio
import logging
import os
import random
from datetime import datetime, timedelta, timezone
import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message

# === Конфигурация ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID", "0"))
TIMEZONE_OFFSET = int(os.getenv("TZ_OFFSET", "5"))  # Челябинск = UTC+5

PRAISES_URL = "https://raw.githubusercontent.com/temnyi74-del/quran-challenge-bot/main/quran_praise_messages.txt"
MOTIVATIONS_URL = "https://raw.githubusercontent.com/temnyi74-del/quran-challenge-bot/refs/heads/main/motivations.txt"

if not BOT_TOKEN or GROUP_ID == 0:
    raise RuntimeError("Нужно задать BOT_TOKEN и GROUP_ID в переменных окружения.")

# === Настройка логирования ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# === Функции загрузки текстов с GitHub ===
async def load_blocks_from_url(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    text = await response.text()
                    blocks = [block.strip() for block in text.split("\n\n") if block.strip()]
                    return blocks
                else:
                    logging.warning(f"Не удалось загрузить данные: {url}. Код: {response.status}")
                    return []
    except Exception as e:
        logging.warning(f"Ошибка при загрузке {url}: {e}")
        return []

# === Обработка фото в группе ===
@dp.message(F.chat.id == GROUP_ID, F.photo)
async def handle_photo(message: Message):
    try:
        praises = await load_blocks_from_url(PRAISES_URL)
        if praises:
            praise = random.choice(praises)
            await message.answer(praise, reply_to_message_id=message.message_id)
    except Exception as e:
        logger.error(f"Ошибка при обработке фото: {e}")

# === Вспомогательные функции времени ===
def local_now() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=TIMEZONE_OFFSET)

def next_time(hour: int, minute: int = 0) -> datetime:
    now = local_now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    return target

# === Цикл мотивашек ===
async def daily_motivation_loop():
    while True:
        try:
            target = next_time(22, 0)
            sleep_sec = (target - local_now()).total_seconds()
            logger.info(f"Мотивация будет отправлена в {target}")
            await asyncio.sleep(sleep_sec)

            motivations = await load_blocks_from_url(MOTIVATIONS_URL)
            if motivations:
                text = "Сегодня не все отметились.\n" + random.choice(motivations)
                await bot.send_message(GROUP_ID, text)
        except Exception as e:
            logger.error(f"Ошибка в daily_motivation_loop: {e}")
        await asyncio.sleep(60)

# === Цикл напоминания о посте (ср/вс) ===
POST_REMINDERS = [
    "Завтра — день желательного поста, не забудьте, ин шаа Аллах!",
    "Пусть завтра Всевышний даст силы держать пост. Это сунна!",
    "Кто постится по понедельникам и четвергам — следует Сунне Пророка ﷺ. Не забудь про завтрашний пост!"
]

async def fasting_reminder_loop():
    while True:
        try:
            target = next_time(21, 0)
            sleep_sec = (target - local_now()).total_seconds()
            await asyncio.sleep(sleep_sec)

            weekday = local_now().weekday()
            if weekday in [2, 6]:  # среда и воскресенье
                reminder = random.choice(POST_REMINDERS)
                await bot.send_message(GROUP_ID, reminder)
        except Exception as e:
            logger.error(f"Ошибка в fasting_reminder_loop: {e}")
        await asyncio.sleep(60)

# === Обработка /start в ЛС ===
@dp.message(F.chat.type == "private", F.text == "/start")
async def start_command(message: Message):
    await message.answer("Ассаламу алейкум! Я бот напоминалка о Коране.")

# === HTTP-сервер для Render — чтобы бот не засыпал ===
async def handle(request):
    return web.Response(text="Bot is alive")

async def start_web():
    app = web.Application()
    app.router.add_get("/", handle)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, port=int(os.environ.get("PORT", 8080)))
    await site.start()

# === Основной запуск ===
async def main():
    logger.info("Бот запускается...")

    asyncio.create_task(daily_motivation_loop())
    asyncio.create_task(fasting_reminder_loop())
    asyncio.create_task(start_web())

    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
