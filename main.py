import asyncio
import logging
from bot import bot, dp
from database import db
from tasks import start_price_monitoring

logging.basicConfig(level=logging.INFO)

async def main():
    print("🚀 Starting Steam Bot System (v1.0)...")

    await db.connect()

    asyncio.create_task(start_price_monitoring())
    print("✅ Background monitoring started")

    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Bot is online and ready!")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 System stopped.")