import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import BOT_TOKEN, ADMIN_ID, CARD_NUMBER, CARD_NAME, BASE_URL

logging.basicConfig(level=logging.INFO)

# DefaultBotProperties o'rniga to'g'ridan-to'g'ri parse_mode beramiz
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.MARKDOWN)
dp = Dispatcher()


@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    """Start komandasi handler"""
    try:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📅 Obuna bo'lish", callback_data="subscribe")]
        ])
        await message.answer(
            "Assalomu alaykum!\nObuna bo'lish uchun tugmani bosing 👇", 
            reply_markup=kb
        )
    except Exception as e:
        logging.error(f"Start handler xatolik: {e}")


@dp.callback_query(F.data == "subscribe")
async def show_subscription_options(callback: types.CallbackQuery):
    buttons = []
    for m in [1, 2, 3, 6, 9, 12]:
        buttons.append(InlineKeyboardButton(text=f"{m} oy", callback_data=f"month_{m}"))

    kb = InlineKeyboardMarkup(inline_keyboard=[buttons[i:i+3] for i in range(0, len(buttons), 3)])
    await callback.answer()
    await callback.message.edit_text("Nechi oylik obuna olmoqchisiz?", reply_markup=kb)

@dp.callback_query(F.data.startswith("month_"))
async def show_price(callback: types.CallbackQuery):
    months = int(callback.data.split("_")[1])
    price = months * 36000
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅ Orqaga", callback_data="subscribe")],
        [InlineKeyboardButton(text="📋 Karta raqamini nusxalash", callback_data="copy_card")],
        [InlineKeyboardButton(text="📤 To‘lov chekini yuborish", callback_data="send_receipt")]
    ])
    await callback.answer()
    await callback.message.edit_text(
        f"📅 {months} oylik obuna narxi: {price:,} so‘m\n\n"
        f"Karta: `{CARD_NUMBER}`\nEgasi: {CARD_NAME}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb
    )

@dp.callback_query(F.data == "copy_card")
async def copy_card(callback: types.CallbackQuery):
    # Karta raqami va "To'lov chekini yuborish" tugmasi birga chiqadi
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 To‘lov chekini yuborish", callback_data="send_receipt")]
    ])
    await callback.message.answer(f"💳 Karta raqami: `{CARD_NUMBER}`\n\nEndi to'lov chekini yuboring.", parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    await callback.answer("Karta raqamini xabardan oson nusxalashingiz mumkin", show_alert=True)

@dp.callback_query(F.data == "send_receipt")
async def ask_receipt(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer("📤 To‘lov chekingizni shu yerga rasm sifatida yuboring")

@dp.message(F.photo)
async def receive_receipt(message: types.Message):
    caption = f"💳 Yangi to‘lov!\n👤 {message.from_user.full_name}"
    await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=caption)
    # Foydalanuvchi ID raqamini admin uchun alohida xabar sifatida yuborish
    await bot.send_message(ADMIN_ID, f"🆔 Foydalanuvchi ID: `{message.from_user.id}`", parse_mode=ParseMode.MARKDOWN)
    # Foydalanuvchiga "Yana to'lov qilish" tugmasi
    user_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Yana to‘lov qilish", callback_data="subscribe")]
    ])
    await message.answer("✅ Chekingiz adminga yuborildi.", reply_markup=user_kb)

async def main():
    try:
        # Webhook ni o'rnatish
        webhook_url = f"{BASE_URL}/tg/webhook"
        await bot.delete_webhook()  # Avval eski webhook ni o'chiramiz
        await bot.set_webhook(url=webhook_url)
        print(f"Webhook muvaffaqiyatli o'rnatildi: {webhook_url}")
    except Exception as e:
        print(f"Webhook o'rnatishda xatolik: {e}")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
    asyncio.run(main())
