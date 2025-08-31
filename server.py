
import os
import asyncio
import traceback
import json
from datetime import datetime, timedelta
from threading import Thread

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from aiogram import types

from config import BOT_TOKEN, BASE_URL, ADMIN_ID
# Import the bot and dispatcher from bot.py
from bot import bot, dp, setup_dispatcher

# --- Background asyncio loop for aiogram ---
loop = asyncio.new_event_loop()

def run_async_loop():
    asyncio.set_event_loop(loop)
    setup_dispatcher(dp)  # Initialize all handlers
    loop.run_forever()

thread = Thread(target=run_async_loop, daemon=True)
thread.start()

VERSION = 'srv-refactor-2' # Version updated

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

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
    try:
        update_data = request.get_json(force=True)
        update = types.Update(**update_data)
        
        async def process():
            await dp.feed_update(bot=bot, update=update)

        asyncio.run_coroutine_threadsafe(process(), loop)
        return 'OK', 200
    except Exception as e:
        print(f"ERROR: Webhook handling error: {e}")
        traceback.print_exc()
        return 'Internal Server Error', 500

@app.route('/')
def index():
    return send_from_directory('static', 'admin.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('static', path)

@app.route('/_version')
def _version():
    return jsonify({'version': VERSION})


# API endpoints for subscription management
@app.route('/api/subscriptions')
def get_subscriptions():
    try:
        subscriptions = load_subscriptions()
        result = []
        for uid, data in subscriptions.items():
            result.append({
                'uid': uid,
                'expiry': data['expiry'],
                'note': data.get('note', '')
            })
        return jsonify(result)
    except Exception as e:
        print(f"ERROR: get_subscriptions error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/subscription', methods=['POST'])
def add_subscription():
    try:
        data = request.get_json()
        uid = str(data['uid'])
        days = int(data['days'])
        note = data.get('note', '')
        
        subscriptions = load_subscriptions()
        
        expiry = datetime.now() + timedelta(days=days)
        
        subscriptions[uid] = {
            'expiry': expiry.isoformat(),
            'note': note
        }
        
        save_subscriptions(subscriptions)
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"ERROR: add_subscription error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/subscription/add', methods=['POST'])
def add_days():
    try:
        data = request.get_json()
        uid = str(data['uid'])
        add_days = int(data['add'])
        
        subscriptions = load_subscriptions()
        
        if uid not in subscriptions:
            return jsonify({'error': 'User not found'}), 404
            
        current_expiry = datetime.fromisoformat(subscriptions[uid]['expiry'])
        new_expiry = current_expiry + timedelta(days=add_days)
        subscriptions[uid]['expiry'] = new_expiry.isoformat()
        
        save_subscriptions(subscriptions)
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"ERROR: add_days error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/subscription/reset', methods=['POST'])
def reset_subscription():
    try:
        data = request.get_json()
        uid = str(data['uid'])
        
        subscriptions = load_subscriptions()
        
        if uid not in subscriptions:
            return jsonify({'error': 'User not found'}), 404
            
        # Set expiry to current time to make it expired
        subscriptions[uid]['expiry'] = datetime.now().isoformat()
        
        save_subscriptions(subscriptions)
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"ERROR: reset_subscription error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/subscription/delete', methods=['POST'])
def delete_subscription():
    try:
        data = request.get_json()
        uid = str(data['uid'])
        
        subscriptions = load_subscriptions()
        
        if uid in subscriptions:
            del subscriptions[uid]
            save_subscriptions(subscriptions)
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        print(f"ERROR: delete_subscription error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/subscription/note', methods=['POST'])
def update_note():
    try:
        data = request.get_json()
        uid = str(data['uid'])
        note = data['note']
        
        subscriptions = load_subscriptions()
        
        if uid not in subscriptions:
            return jsonify({'error': 'User not found'}), 404
            
        subscriptions[uid]['note'] = note
        save_subscriptions(subscriptions)
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"ERROR: update_note error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    _setup_webhook()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
else: # When run by Gunicorn
    _setup_webhook()
