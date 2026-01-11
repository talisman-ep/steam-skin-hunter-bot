import os

BASE_URL = "https://steamcommunity.com/market/priceoverview/"
APP_ID = 730
CURRENCY = 1
UAH_RATE = 42.5

BOT_TOKEN = os.getenv("BOT_TOKEN")

DB_HOST = os.getenv("DB_HOST", "localhost")

DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "steam_skins_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")