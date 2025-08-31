import logging
import json
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Message

# Loggingni sozlash
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test handler - bu har doim ishlashi kerak
async def start_cmd(message: Message):
    logger.info(f"Received /start command from user {message.from_user.id}")
    await message.answer("Salom! Bot ishlayapti.")

# Oddiy xabarlar uchun handler
async def echo_handler(message: Message):
    logger.info(f"Received message from user {message.from_user.id}: {message.text}")
    await message.answer(f"Siz yubordingiz: {message.text}")

# Qolgan barcha funksiyalar
def load_subscriptions():
    """Obunachilarni JSON fayldan yuklash"""
    try:
        with open('subscriptions.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_subscriptions(subscriptions):
    """Obunachilarni JSON faylga saqlash"""
    with open('subscriptions.json', 'w') as f:
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

# Handlerlarni ro'yxatdan o'tkazish funksiyasi (server.py uchun)
def setup_dispatcher(dispatcher):
    """Bot uchun barcha handlerlarni ro'yxatdan o'tkazish"""
    logger.info("Setting up dispatcher with handlers")
    dispatcher.message.register(start_cmd, CommandStart())
    dispatcher.message.register(echo_handler)
