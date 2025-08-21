import asyncio
import logging
import os
from datetime import datetime, time, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message

logging.basicConfig(level=logging.INFO)

# ==== Настройки ====
BOT_TOKEN = os.getenv("BOT_TOKEN")  # токен бота
GROUP_ID = int(os.getenv("GROUP_ID"))  # id группы (со знаком -100...)
TIMEZONE_OFFSET = 5  # твой часовой пояс относительно UTC (например +5)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==== 30 мотивашек ====
MOTIVATIONS = [
    "Сегодня не все отметились. Давайте завтра будем активнее, ин ша Аллах!",
    "Не забывайте про чтение Корана — это свет в сердце 🌙",
    "Аллах любит тех, кто старается ради Него 🤲",
    "Кто держится за Коран — тот никогда не заблудится 📖",
    "Каждый день с Кораном — приближение к Раю 🌿",
    "Пусть завтра будет больше барракята в наших стараниях 🌸",
    "Давайте вместе укрепим нашу связь с Книгой Аллаха 💎",
    "Аллах говорит: 'Воистину, этим Кораном направляет Он кого пожелает' (39:23)",
    "С каждым аятом приближаемся к довольству Аллаха 🌹",
    "Завтра ещё один шанс проявить усердие 💪",
    "Коран — лучший друг и помощник в этом мире и в Ахира 🌍",
    "Кто читает Коран — тот наполняет сердце светом ✨",
    "Аллах возвышает людей через Коран 🕌",
    "Усердие сегодня — награда в Судный день 🌟",
    "Слово Аллаха — лекарство для душ и сердец ❤️",
    "Не теряй возможности приблизиться к Аллаху через чтение 📖",
    "Коран ведёт к счастью и спокойствию 🕊️",
    "Пусть наши сердца будут мягкими благодаря Корану 🌷",
    "Аллах облегчит путь в Рай тем, кто учит Коран 🌼",
    "Каждое прочитанное слово — это награда 🌺",
    "Пусть Коран будет нашим заступником в Судный день 🌙",
    "Нет усталости, когда рядом Коран 🌿",
    "Аллах открывает пути тем, кто держится за Его Книгу 🚪",
    "Слова Аллаха сильнее любых трудностей 💪",
    "Коран укрепляет иман и приносит спокойствие 🌸",
    "Каждый аят — это обращение Всевышнего к тебе ✨",
    "Аллах любит тех, кто очищает своё сердце Кораном 💖",
    "Не позволяй дню пройти без аятов Корана 🌅",
    "Коран — источник силы и терпения 🌟",
    "В каждом дне ищи минуту для Корана — и увидишь барракат 🌼",
]

# индекс текущей мотивашки
motivation_index = 0

# ==== Реакция на фото ====
@dp.message()
async def handle_message(message: types.Message):
    if message.chat.id == GROUP_ID and message.photo:
        name = message.from_user.full_name or message.from_user.first_name or "брат"
        await message.reply(f"""بارك الله فيك 
Пусть Аллаh примет, 
آمين 🤲""")

# ==== Планировщик мотивашек ====
async def send_motivation():
    global motivation_index
    while True:
        now = datetime.utcnow() + timedelta(hours=TIMEZONE_OFFSET)
        target = datetime.combine(now.date(), time(22, 0))  # каждый день в 22:00
        if now > target:
            target += timedelta(days=1)
        wait_seconds = (target - now).total_seconds()
        await asyncio.sleep(wait_seconds)

        # отправляем мотивашку по порядку
        motivation = MOTIVATIONS[motivation_index]
        try:
            await bot.send_message(GROUP_ID, motivation)
        except Exception as e:
            logging.error(f"Ошибка отправки мотивашки: {e}")

        # переходим к следующей, если дошли до конца — начинаем с 0
        motivation_index = (motivation_index + 1) % len(MOTIVATIONS)

# ==== Main ====
async def main():
    asyncio.create_task(send_motivation())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
