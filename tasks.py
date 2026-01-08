import asyncio
import aiohttp
from database import db
from steam_client import SteamClient

async def start_price_monitoring():
    """Фонова функція: перевіряє ціни зі списку відстеження"""
    print("🔄 [Tasks] Price monitoring started...")
    
    while True:
        await asyncio.sleep(5)

        try:
            skins = await db.get_tracked_skins()
            
            if not skins:
                print("💤 [Tasks] Watchlist is empty. Sleeping 60s...")
                await asyncio.sleep(60)
                continue

            client = SteamClient()

            async with aiohttp.ClientSession() as session:
                for skin in skins:
                    _, price = await client.get_price(session, skin)
                    
                    if price:
                        await db.add_price(skin, price)
                    
                    await asyncio.sleep(5)

            print("💤 [Tasks] Cycle finished. Next check in 30 min.")
            await asyncio.sleep(1800)

        except Exception as e:
            print(f"⚠️ [Tasks Error] {e}")
            await asyncio.sleep(60)