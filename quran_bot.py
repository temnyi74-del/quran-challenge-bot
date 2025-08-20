import asyncio, logging, os
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from datetime import datetime, timedelta
import pytz

# Переменные окружения
TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
TZ = pytz.timezone(os.getenv("TIMEZONE", "Asia/Yekaterinburg"))

# Инициализация aiogram v3
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Реакция на фото в нужной группе
@dp.message()
async def handle_message(message: types.Message):
    if message.chat.id == GROUP_ID and message.photo:
        await message.reply(f"МашаАллах, {message.from_user.first_name}! Аллах примет 🤲")

# Ежедневное напоминание в 23:59 по Челябинску
async def reminder():
    while True:
        now = datetime.now(TZ)
        target = now.replace(hour=23, minute=59, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())
        try:
            await bot.send_message(GROUP_ID, "Сегодня не все отметились 😔 Пусть Коран будет светом сердец 🤲")
        except Exception as e:
            logging.error(f"Reminder error: {e}")

async def main():
    logging.basicConfig(level=logging.INFO)
    asyncio.create_task(reminder())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
