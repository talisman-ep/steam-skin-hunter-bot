import asyncio
import random
import aiohttp
from database import db
from steam_client import SteamClient

async def start_monitoring(bot):
    """Background process: checks prices and sends alerts"""
    print("Background monitor started (separate module)...")
    client = SteamClient()
    
    while True:
        try:
            alerts = await db.get_all_alerts()
            
            if not alerts:
                await asyncio.sleep(300)
                continue
            unique_skins = list(set(row['skin_name'] for row in alerts))
            print(f"Monitor: Checking {len(unique_skins)} skins...")

            async with aiohttp.ClientSession() as session:
                for skin_name in unique_skins:
                    _, current_price = await client.get_price(session, skin_name)
                    
                    if current_price:
                        await db.add_price(skin_name, current_price)

                        for alert in alerts:
                            if alert['skin_name'] == skin_name:
                                target = alert['target_price']
                                user_id = alert['user_id']
                                
                                if current_price <= target:
                                    try:
                                        await bot.send_message(
                                            user_id,
                                            f"🚨 **АЛЕРТ! ЦІНА ВПАЛА!**\n\n"
                                            f"🔹 **{skin_name}**\n"
                                            f"📉 Поточна: **{current_price} $**\n"
                                            f"🎯 Твоя ціль: {target} $\n\n"
                                            f"Сповіщення спрацювало і вимкнено.",
                                            parse_mode="Markdown"
                                        )
                                        await db.remove_alert(user_id, skin_name)
                                    except Exception as e:
                                        print(f"Failed to notify {user_id}: {e}")

                    await asyncio.sleep(random.uniform(5, 10))
            
            print("Monitor cycle finished.")

        except Exception as e:
            print(f"Monitor crashed: {e}")

        await asyncio.sleep(300)