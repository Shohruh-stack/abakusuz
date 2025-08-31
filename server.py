
import os
import asyncio
import traceback
import gc
from threading import Thread

from flask import Flask, request, jsonify
from aiogram import types

from config import BOT_TOKEN, BASE_URL
# Import the bot and dispatcher from bot.py
from bot import bot, dp, setup_dispatcher

# --- Background asyncio loop for aiogram ---
loop = asyncio.new_event_loop()

def run_async_loop():
    asyncio.set_event_loop(loop)
    setup_dispatcher(dp)
    gc.enable()  # GC yoqildi
    gc.set_threshold(700, 10, 10)  # GC parametrlari
    try:
        loop.run_forever()
    finally:
        loop.close() 

thread = Thread(target=run_async_loop, daemon=True)
thread.start()

VERSION = 'srv-refactor-2' # Version updated

app = Flask(__name__)

def _setup_webhook():
    if not BOT_TOKEN or not BASE_URL:
        print("BOT_TOKEN or BASE_URL not set; skipping webhook setup")
        return

    webhook_url = BASE_URL.rstrip('/') + '/tg/webhook'

    async def set_hook():
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            await bot.set_webhook(webhook_url)
            print(f"INFO: Webhook set to {webhook_url}")
        except Exception as e:
            print(f"ERROR: Webhook setup error: {e}")

    asyncio.run_coroutine_threadsafe(set_hook(), loop)

@app.route('/tg/webhook', methods=['POST'])
def webhook_handler():
    if request.content_length > 1024 * 10:  # 10KB cheklovi
        return 'Payload too large', 413
    
    try:
        update_data = request.get_json(force=True)
        update = types.Update(**update_data)
        
        async def process():
            try:
                await dp.feed_update(bot=bot, update=update)
            finally:
                gc.collect()  # Xotirani tozalash

        asyncio.run_coroutine_threadsafe(process(), loop)
        return 'OK', 200
    except Exception as e:
        print(f"ERROR: Webhook handling error: {e}")
        traceback.print_exc()
        return 'Internal Server Error', 500

@app.route('/')
def index():
    return "Bot is running!"

@app.route('/_version')
def _version():
    return jsonify({'version': VERSION})

if __name__ == "__main__":
    _setup_webhook()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
else: # When run by Gunicorn
    _setup_webhook()
