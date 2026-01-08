import aiohttp
import re
import asyncio
import urllib.parse
from config import BASE_URL, APP_ID, CURRENCY

class SteamClient:
    def __init__(self):
        self.base_url = BASE_URL
        self.inventory_url = "https://steamcommunity.com/inventory/{}/730/2"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en-US,en;q=0.9",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://steamcommunity.com/market/"
        }

    async def get_price(self, session, item_name: str):
        encoded_name = urllib.parse.quote(item_name)
        url = f"{self.base_url}?appid={APP_ID}&currency={CURRENCY}&market_hash_name={encoded_name}"
        
        try:
            await asyncio.sleep(0.5) 
            
            async with session.get(url, headers=self.headers) as response:
                if response.status == 429:
                    print(f"⚠️ Rate Limit (429) for: {item_name}")
                    return item_name, None
                
                if response.status != 200:
                    print(f"❌ Error {response.status} for: {item_name}")
                    return item_name, None
                
                data = await response.json()
                if data and data.get("success") is True:
                    raw_price = data.get("lowest_price")
                    if raw_price:
                        clean_price = raw_price.replace("$", "").replace(",", "").replace("USD", "").strip()
                        try:
                            return item_name, float(clean_price)
                        except ValueError:
                            return item_name, float(clean_price.replace(",", ""))
                            
                return item_name, None
        except Exception as e:
            print(f"[Price Error] {item_name}: {e}")
            return item_name, None

    def extract_steam_id(self, url: str):
        match = re.search(r"7656\d{13}", url)
        if match:
            return match.group(0)
        return None

    async def get_inventory(self, session, steam_id: str):
        url = self.inventory_url.format(steam_id)

        full_inventory = {}
        
        params = {"l": "english", "count": 100}
        headers = self.headers.copy()
        headers["Referer"] = f"https://steamcommunity.com/profiles/{steam_id}/inventory"
        
        start_assetid = None
        page = 1
        
        print(f"📡 Starting inventory scan for {steam_id}...")

        while True:
            if start_assetid:
                params["start_assetid"] = start_assetid
            
            try:
                if page > 1:
                    await asyncio.sleep(1.5)

                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 429:
                        print("⏳ Rate limit hit! Waiting 5 seconds...")
                        await asyncio.sleep(5)
                        continue
                        
                    if response.status != 200:
                        print(f"❌ Error on page {page}: {response.status}")
                        break 
                    
                    data = await response.json()
                    if not data:
                        break

                    assets = data.get("assets", [])
                    descriptions = data.get("descriptions", [])
                    
                    if not assets:
                        break

                    print(f"   📄 Page {page}: found {len(assets)} items")

                    item_names = {}
                    for desc in descriptions:
                        if desc.get("marketable") == 1:
                            item_names[desc["classid"]] = desc["market_hash_name"]

                    for asset in assets:
                        classid = asset["classid"]
                        if classid in item_names:
                            skin_name = item_names[classid]
                            full_inventory[skin_name] = full_inventory.get(skin_name, 0) + 1

                    if "last_assetid" in data:
                        start_assetid = data["last_assetid"]
                        page += 1

                        if page > 20: 
                            print("⚠️ Bot page limit reached.")
                            break
                    else:
                        break

            except Exception as e:
                print(f"[Pagination Error] {e}")
                break
        
        print(f"✅ Scan complete. Unique slots: {len(full_inventory)}")
        return full_inventory