import logging
import json
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from config import BOT_TOKEN, ADMIN_ID, CARD_NUMBER, CARD_NAME

logging.basicConfig(level=logging.INFO)

# Bot va dispatcher obyektlarini yaratish
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Obunachilarni saqlash fayli
SUBSCRIPTIONS_FILE = os.path.join(os.path.dirname(__file__), 'subscriptions.json')

def load_subscriptions():
    """Obunachilarni JSON fayldan yuklash"""
    try:
        with open(SUBSCRIPTIONS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_subscriptions(subscriptions):
    """Obunachilarni JSON faylga saqlash"""
    with open(SUBSCRIPTIONS_FILE, 'w') as f:
        json.dump(subscriptions, f, indent=2)

def is_subscribed(user_id):
    """Foydalanuvchi obunachimi yoki yo'qligini tekshirish"""
    subscriptions = load_subscriptions()
    user_id_str = str(user_id)
    
    if user_id_str in subscriptions:
        expiry_str = subscriptions[user_id_str]['expiry']
        expiry = datetime.fromisoformat(expiry_str)
        return datetime.now() < expiry
    return False

# /start buyrug'i uchun handler
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    logging.info(f"Received /start command from user {message.from_user.id}")
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton("Obuna bo'lish"))
    keyboard.add(types.KeyboardButton("Obunani tekshirish"))
    await message.answer("Assalomu alaykum! Obuna bo'lish uchun quyidagi tugmani bosing:", reply_markup=keyboard)

# "Obuna bo'lish" tugmasi uchun handler
@dp.message(lambda message: message.text == "Obuna bo'lish")
async def handle_subscription(message: types.Message):
    logging.info(f"Received 'Obuna bo'lish' from user {message.from_user.id}")
    user_id = message.from_user.id
    username = message.from_user.username or "Noma'lum"
    
    # To'lov ma'lumotlarini yuborish
    payment_info = f"""Obuna bo'lish uchun quyidagi karta raqamiga to'lov qiling:

Karta raqami: <code>{CARD_NUMBER}</code>
Karta egasi: <code>{CARD_NAME}</code>

To'lovni amalga oshirgandan so'ng, to'lov chekinining skrinshotini yuboring.

To'lov summasi: 10,000 so'm/oy

Foydalanuvchi ID: <code>{user_id}</code>
Ism: {message.from_user.full_name}
Username: @{username}
"""
    
    await message.answer(payment_info, parse_mode='HTML')
    
    # Administratorga xabar berish
    admin_message = f"""Yangi to'lov so'rovi!

Foydalanuvchi ID: {user_id}
Ism: {message.from_user.full_name}
Username: @{username}
"""
    
    await bot.send_message(ADMIN_ID, admin_message)

# "Obunani tekshirish" tugmasi uchun handler
@dp.message(lambda message: message.text == "Obunani tekshirish")
async def check_subscription(message: types.Message):
    logging.info(f"Received 'Obunani tekshirish' from user {message.from_user.id}")
    user_id = message.from_user.id
    
    if is_subscribed(user_id):
        subscriptions = load_subscriptions()
        expiry_str = subscriptions[str(user_id)]['expiry']
        expiry = datetime.fromisoformat(expiry_str)
        days_left = (expiry - datetime.now()).days
        
        await message.answer(f"Sizning obunangiz faol. {days_left} kun qolgan.")
    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(types.KeyboardButton("Obuna bo'lish"))
        await message.answer("Sizning obunangiz faol emas. Obuna bo'lish uchun quyidagi tugmani bosing:", reply_markup=keyboard)

# Oddiy matnli xabarlar uchun handler
@dp.message()
async def echo(message: types.Message):
    logging.info(f"Received message from user {message.from_user.id}: {message.text}")
    await message.answer("Xabar qabul qilindi. Yordam uchun /start buyrug'ini bosing.")
