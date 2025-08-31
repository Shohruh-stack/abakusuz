import logging
import json
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from config import BOT_TOKEN, ADMIN_ID, CARD_NUMBER, CARD_NAME

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Path to subscriptions file
SUBSCRIPTIONS_FILE = os.path.join(os.path.dirname(__file__), 'subscriptions.json')

def load_subscriptions():
    """Load subscriptions from JSON file"""
    try:
        with open(SUBSCRIPTIONS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_subscriptions(subscriptions):
    """Save subscriptions to JSON file"""
    with open(SUBSCRIPTIONS_FILE, 'w') as f:
        json.dump(subscriptions, f, indent=2)

def is_subscribed(user_id):
    """Check if user is subscribed"""
    subscriptions = load_subscriptions()
    user_id_str = str(user_id)
    
    if user_id_str in subscriptions:
        expiry_str = subscriptions[user_id_str]['expiry']
        expiry = datetime.fromisoformat(expiry_str)
        return datetime.now() < expiry
    return False

def setup_dispatcher(dispatcher):
    """Setup all handlers for the bot"""
    dispatcher.message.register(start_cmd, CommandStart())
    dispatcher.message.register(handle_subscription, lambda message: message.text == "Obuna bo'lish")
    dispatcher.message.register(check_subscription, lambda message: message.text == "Obunani tekshirish")

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton("Obuna bo'lish"))
    keyboard.add(types.KeyboardButton("Obunani tekshirish"))
    await message.answer("Assalomu alaykum! Obuna bo'lish uchun quyidagi tugmani bosing:", reply_markup=keyboard)

@dp.message(lambda message: message.text == "Obuna bo'lish")
async def handle_subscription(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Noma'lum"
    
    # Send payment information
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
    
    # Notify admin
    admin_message = f"""Yangi to'lov so'rovi!

Foydalanuvchi ID: {user_id}
Ism: {message.from_user.full_name}
Username: @{username}
"""
    
    await bot.send_message(ADMIN_ID, admin_message)

@dp.message(lambda message: message.text == "Obunani tekshirish")
async def check_subscription(message: types.Message):
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

# For backwards compatibility
async def start_cmd_old(message: types.Message):
    await start_cmd(message)

async def handle_subscription_old(message: types.Message):
    await handle_subscription(message)
