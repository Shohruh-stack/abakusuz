import os
import hashlib
import hmac
import json
from datetime import datetime, timedelta

from flask import Flask, request, jsonify, send_file, session, redirect
from flask_cors import CORS
# Optional DB import: allow running without Postgres client
try:
    import psycopg2
    import psycopg2.extras
except Exception:
    psycopg2 = None
import asyncio
from aiogram import Bot, types, Dispatcher

from config import BOT_TOKEN, FLASK_SECRET, BASE_URL
from bot import bot, dp  # bot.py dan bot va dispatcher ni import qilamiz

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')
SUBS_JSON = os.path.join(BASE_DIR, 'subscriptions.json')
VERSION = 'srv-json-fallback-3'

# Event loop ni global o'zgaruvchi sifatida saqlash
loop = None

def get_event_loop():
    """Event loop ni olish yoki yaratish"""
    global loop
    if loop is None or loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop

# Bot instance va webhook setup
async def setup_webhook():
    """Bot va webhook ni sozlash"""
    try:
        webhook_url = f"{BASE_URL}/tg/webhook"
        await bot.delete_webhook()  # Avvalgi webhookni o'chirish
        await bot.set_webhook(url=webhook_url)
        print(f"Webhook muvaffaqiyatli o'rnatildi: {webhook_url}")
    except Exception as e:
        print('Webhook o\'rnatishda xatolik:', e)

def init_webhook():
    """Webhook ni sinxron ravishda o'rnatish"""
    loop = get_event_loop()
    loop.run_until_complete(setup_webhook())

# Flask app setup
app = Flask(__name__, static_folder=STATIC_DIR)
app.secret_key = FLASK_SECRET
CORS(app)

# Webhook handler
@app.route('/tg/webhook', methods=['POST'])
def tg_webhook():
    try:
        update = types.Update.model_validate_json(request.get_data().decode('utf-8'))
        loop = get_event_loop()
        loop.run_until_complete(dp.feed_update(bot=bot, update=update))
        return 'OK'
    except Exception as e:
        print('Webhook qayta ishlashda xatolik:', e)
        return 'Error', 500

# Server ishga tushganda webhook ni o'rnatish
if os.environ.get('RENDER'):
    init_webhook()

PORT = os.environ.get('PORT', 5000)

DATABASE_URL = os.getenv("DATABASE_URL", "")
USE_DB = bool(DATABASE_URL) and (psycopg2 is not None)


def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set. Use a free Postgres like Neon and set DATABASE_URL env var.")
    if psycopg2 is None:
        raise RuntimeError("psycopg2 is not installed. Install psycopg2-binary or unset DATABASE_URL to use JSON storage.")
    # Ensure SSL in hosted environments (Neon/Supabase typically require it)
    if 'sslmode' not in DATABASE_URL:
        dsn = DATABASE_URL + ("?sslmode=require" if '?' not in DATABASE_URL else "&sslmode=require")
    else:
        dsn = DATABASE_URL
    return psycopg2.connect(dsn)


def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS subscriptions (
                  uid TEXT PRIMARY KEY,
                  expiry TIMESTAMP WITH TIME ZONE,
                  note TEXT
                );
                """
            )
            conn.commit()

if DATABASE_URL and psycopg2 is not None:
    init_db()
else:
    print("DATABASE_URL not set or psycopg2 missing; skipping DB init")

# JSON fallback storage

def load_json():
    try:
        with open(SUBS_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        print('Failed to load subscriptions.json:', e)
        return {}


def save_json(data: dict):
    try:
        with open(SUBS_JSON, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print('Failed to save subscriptions.json:', e)


def file_list_subs():
    data = load_json()
    out = []
    for uid, v in data.items():
        out.append({
            'uid': uid,
            'expiry': v.get('expiry'),
            'note': v.get('note', '')
        })
    return out


def file_set_days(uid: str, new_days: int, note: str = None):
    data = load_json()
    now = datetime.utcnow()
    v = data.get(uid) or {}
    expiry_str = v.get('expiry')
    base = now
    if expiry_str:
        try:
            old = datetime.fromisoformat(expiry_str)
            base = old if old > now else now
        except Exception:
            base = now
    new_expiry = base + timedelta(days=new_days)
    v['expiry'] = new_expiry.replace(microsecond=0).isoformat()
    if note is not None:
        v['note'] = note
    elif 'note' not in v:
        v['note'] = ''
    data[uid] = v
    save_json(data)


def file_add_days(uid: str, add_days: int):
    data = load_json()
    if uid not in data:
        raise ValueError('Foydalanuvchi topilmadi')
    now = datetime.utcnow()
    expiry_str = data[uid].get('expiry')
    base = now
    if expiry_str:
        try:
            old = datetime.fromisoformat(expiry_str)
            base = old if old > now else now
        except Exception:
            base = now
    new_expiry = base + timedelta(days=add_days)
    data[uid]['expiry'] = new_expiry.replace(microsecond=0).isoformat()
    save_json(data)


def file_reset(uid: str):
    data = load_json()
    if uid not in data:
        raise ValueError('Foydalanuvchi topilmadi')
    data[uid]['expiry'] = datetime.utcnow().replace(microsecond=0).isoformat()
    save_json(data)


def file_set_note(uid: str, note: str):
    data = load_json()
    if uid not in data:
        raise ValueError('Foydalanuvchi topilmadi')
    data[uid]['note'] = note
    save_json(data)


def file_delete(uid: str):
    data = load_json()
    if uid not in data:
        raise ValueError('Foydalanuvchi topilmadi')
    del data[uid]
    save_json(data)


def file_status(uid: str):
    data = load_json()
    v = data.get(uid)
    if not v or not v.get('expiry'):
        return {'subscribed': False, 'days_left': 0}
    try:
        expiry = datetime.fromisoformat(v['expiry'])
    except Exception:
        return {'subscribed': False, 'days_left': 0}
    now = datetime.utcnow()
    days_left = max(0, (expiry - now).days)
    return {'subscribed': days_left > 0, 'days_left': days_left}


# Generic dispatchers

def list_subs():
    return db_list_subs() if USE_DB else file_list_subs()

def set_days(uid: str, days: int, note: str = None):
    return db_set_days(uid, days, note) if USE_DB else file_set_days(uid, days, note)


def add_days(uid: str, add: int):
    return db_add_days(uid, add) if USE_DB else file_add_days(uid, add)


def reset(uid: str):
    return db_reset(uid) if USE_DB else file_reset(uid)


def set_note(uid: str, note: str):
    return db_set_note(uid, note) if USE_DB else file_set_note(uid, note)


def delete(uid: str):
    return db_delete(uid) if USE_DB else file_delete(uid)


def status(uid: str):
    return db_status(uid) if USE_DB else file_status(uid)

# -------------- Static pages --------------
@app.route('/admin.html')
def serve_admin():
    return send_file(os.path.join(STATIC_DIR, 'admin.html'))


@app.route('/login.html')
def serve_login():
    return send_file(os.path.join(BASE_DIR, 'login.html'))


# -------------- Auth (Telegram Login Widget) --------------
def check_auth(data):
    auth_data = dict(data)
    hash_to_check = auth_data.pop('hash', None)
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(auth_data.items()))
    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
    hmac_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return hmac_hash == hash_to_check


@app.route("/auth")
def auth():
    if check_auth(request.args):
        session['tg_id'] = request.args['id']
        session['username'] = request.args.get('username', '')
        return f"Xush kelibsiz, {session['username'] or session['tg_id']}!"
    return "Auth xatosi"


@app.route("/")
def index():
    if 'tg_id' in session:
        return f"Siz tizimga kirdingiz: {session['username'] or session['tg_id']}"
    return redirect('/login.html')


# -------------- DB helpers --------------
def db_list_subs():
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT uid, expiry, note FROM subscriptions")
            rows = cur.fetchall()
            return [
                {
                    'uid': r['uid'],
                    'expiry': r['expiry'].replace(microsecond=0).isoformat() if r['expiry'] else None,
                    'note': r['note']
                }
                for r in rows
            ]


def db_set_days(uid: str, new_days: int, note: str = None):
    # Sets subscription to now + days, or extends if already active
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT expiry FROM subscriptions WHERE uid=%s", (uid,))
            row = cur.fetchone()
            now = datetime.utcnow()
            base = now
            if row and row[0]:
                old_expiry = row[0]
                if old_expiry > now:
                    base = old_expiry
            
            new_expiry = base + timedelta(days=new_days)

            # Use INSERT ON CONFLICT to handle both new and existing users for expiry
            cur.execute(
                """
                INSERT INTO subscriptions (uid, expiry) VALUES (%s, %s)
                ON CONFLICT (uid) DO UPDATE SET expiry = EXCLUDED.expiry
                """,
                (uid, new_expiry)
            )

            # If a note is provided, update it. This works for both new and existing users
            # because the previous query ensures the user exists.
            if note is not None:
                cur.execute(
                    "UPDATE subscriptions SET note=%s WHERE uid=%s",
                    (note, uid)
                )
            conn.commit()


def db_add_days(uid: str, add_days: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT expiry FROM subscriptions WHERE uid=%s", (uid,))
            row = cur.fetchone()
            now = datetime.utcnow()
            base = row[0] if row and row[0] and row[0] > now else now
            new_expiry = base + timedelta(days=add_days)
            cur.execute(
                "UPDATE subscriptions SET expiry=%s WHERE uid=%s",
                (new_expiry, uid)
            )
            if cur.rowcount == 0:
                raise ValueError('Foydalanuvchi topilmadi')
            conn.commit()


def db_reset(uid: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE subscriptions SET expiry=%s WHERE uid=%s", (datetime.utcnow(), uid))
            if cur.rowcount == 0:
                raise ValueError('Foydalanuvchi topilmadi')
            conn.commit()


def db_set_note(uid: str, note: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM subscriptions WHERE uid=%s", (uid,))
            if cur.fetchone() is None:
                raise ValueError('Foydalanuvchi topilmadi')
            cur.execute("UPDATE subscriptions SET note=%s WHERE uid=%s", (note, uid))
            conn.commit()


def db_delete(uid: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM subscriptions WHERE uid=%s", (uid,))
            if cur.rowcount == 0:
                raise ValueError('Foydalanuvchi topilmadi')
            conn.commit()


def db_status(uid: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT expiry FROM subscriptions WHERE uid=%s", (uid,))
            row = cur.fetchone()
            if not row or not row[0]:
                return {'subscribed': False, 'days_left': 0}
            expiry = row[0]
            now = datetime.utcnow()
            days_left = max(0, (expiry - now).days)
            return {'subscribed': days_left > 0, 'days_left': days_left}


# Debug info
@app.route('/_debug')
def _debug():
    return jsonify({
        'USE_DB': USE_DB,
        'DATABASE_URL_set': bool(DATABASE_URL),
        'SUBS_JSON': SUBS_JSON,
        'version': VERSION
    })

@app.route('/_version')
def _version():
    return jsonify({'version': VERSION, 'subs_json': SUBS_JSON})

# -------------- API --------------
@app.route('/api/subscriptions', methods=['GET'])
def api_subscriptions():
    try:
        data = list_subs()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/subscription', methods=['POST'])
def api_subscription():
    data = request.get_json(force=True)
    uid = str(data.get('uid'))
    days = int(data.get('days', 0))
    note = data.get('note')
    if not uid or days < 1:
        return jsonify({'error': "UID va kun to‘g‘ri kiritilsin"}), 400
    try:
        set_days(uid, days, note)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/subscription/add', methods=['POST'])
def api_subscription_add():
    data = request.get_json(force=True)
    uid = str(data.get('uid'))
    add = int(data.get('add', 0))
    if not uid or add < 1:
        return jsonify({'error': "UID va kunni to‘g‘ri kiriting"}), 400
    try:
        add_days(uid, add)
        return jsonify({'ok': True})
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/subscription/reset', methods=['POST'])
def api_subscription_reset():
    data = request.get_json(force=True)
    uid = str(data.get('uid'))
    if not uid:
        return jsonify({'error': "UID kiritilmadi"}), 400
    try:
        reset(uid)
        return jsonify({'ok': True})
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/subscription/note', methods=['POST'])
def api_subscription_note():
    data = request.get_json(force=True)
    uid = str(data.get('uid'))
    note = data.get('note', '')
    if not uid:
        return jsonify({'error': "UID kiritilmadi"}), 400
    try:
        set_note(uid, note)
        return jsonify({'ok': True})
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/subscription/delete', methods=['POST'])
def api_subscription_delete():
    data = request.get_json(force=True)
    uid = str(data.get('uid'))
    if not uid:
        return jsonify({'error': "UID kiritilmadi"}), 400
    try:
        delete(uid)
        return jsonify({'ok': True})
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/subscription/status', methods=['GET'])
def api_subscription_status():
    tg_id = request.args.get('tg_id')
    if not tg_id:
        # Fallback to session if available (after /login.html auth)
        tg_id = session.get('tg_id')
    if not tg_id:
        return jsonify({'subscribed': False, 'days_left': 0})
    try:
        return jsonify(status(str(tg_id)))
    except Exception:
        return jsonify({'subscribed': False, 'days_left': 0})


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    init_webhook()  # Webhook ni o'rnatish
    app.run(host='0.0.0.0', port=port)
