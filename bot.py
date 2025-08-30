import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from config import BOT_TOKEN

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def setup_dispatcher(dispatcher):
    """Setup all handlers for the bot"""
    dispatcher.message.register(start_cmd, CommandStart())
    dispatcher.message.register(handle_subscription, lambda message: message.text == "Obuna bo'lish")

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("Obuna bo'lish"))
    await message.answer("Assalomu alaykum! Obuna bo'lish uchun quyidagi tugmani bosing:", reply_markup=keyboard)

@dp.message(lambda message: message.text == "Obuna bo'lish")
async def handle_subscription(message: types.Message):
    await message.answer("Obuna bo'lish uchun to'lov qilishingiz kerak. Iltimos, administrator bilan bog'laning.")
