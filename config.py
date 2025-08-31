import os

# Telegram Bot configuration (do NOT hardcode secrets in production)
# Uses environment variables if set; otherwise falls back to the values you provided.
BOT_TOKEN = os.getenv("8167279999:AAFfY47MaQlqayKbRyecXIXnjoWyfMjpyOk")  # Must be set in environment variables for security

_admin_id = os.getenv("ADMIN_ID") or "475202258"
try:
    ADMIN_ID = int(_admin_id) if _admin_id else None
except ValueError:
    ADMIN_ID = None

CARD_NUMBER = os.getenv("CARD_NUMBER") or "4067070006008515"
CARD_NAME = os.getenv("CARD_NAME") or "SHOXRUX XOJIBAYEV"

# Flask / Web configuration
FLASK_SECRET = os.getenv("FLASK_SECRET", "change-me")
# This should be your public bot server URL provided by render.com
BASE_URL = os.getenv("BASE_URL")  # Must be set in environment variables

# Fallback for local development
if not BASE_URL:
    BASE_URL = "https://abakusuz.onrender.com"  # Change this to your actual Render.com URL
