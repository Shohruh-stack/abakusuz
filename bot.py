import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher, types, F
from aiogram.client.bot import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import BOT_TOKEN, ADMIN_ID, CARD_NUMBER, CARD_NAME

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()


@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Obuna bo‘lish", callback_data="subscribe")]
    ])
    await message.answer("Assalomu alaykum!\nObuna bo‘lish uchun tugmani bosing 👇", reply_markup=kb)


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
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
