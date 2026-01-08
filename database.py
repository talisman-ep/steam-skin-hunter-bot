import asyncpg
from config import DB_HOST, DB_NAME, DB_PASS, DB_PORT, DB_USER

class Database():
    def __init__(self):
        self.pool = None
        
    async def connect(self):
        if not self.pool:
            print("🔌 Connecting to database...")
            try:
                self.pool = await asyncpg.create_pool(
                    user=DB_USER,
                    password=DB_PASS,
                    database=DB_NAME,
                    host=DB_HOST,
                    port=DB_PORT
                )
                print("✅ Database connected successfully!")
            except Exception as e:
                print(f"❌ Connection error: {e}")
            
    async def add_price(self, skin_name: str, price: float):
        if not self.pool:
            await self.connect()

        query = "INSERT INTO skin_prices (skin_name, price) VALUES ($1, $2)"
        try:
            async with self.pool.acquire() as connection:
                await connection.execute(query, skin_name, price)
        except Exception as e:
            print(f"❌ Database write error: {e}")
            
    async def get_latest_price(self):
        if not self.pool:
            await self.connect()
            
        query = """
            SELECT DISTINCT ON (skin_name) skin_name, price, currency, recorded_at 
            FROM skin_prices 
            ORDER BY skin_name, recorded_at DESC
        """
        try:
            async with self.pool.acquire() as connection:
                rows = await connection.fetch(query)
                return rows
        except Exception as e:
            print(f"❌ Database read error: {e}")
            return []
        
    async def add_track_skin(self, skin_name: str):
        if not self.pool:
            await self.connect()
            
        query = """
            INSERT INTO tracked_items (skin_name) 
            VALUES ($1) 
            ON CONFLICT (skin_name) DO NOTHING
        """
        try:
            async with self.pool.acquire() as connection:
                await connection.execute(query, skin_name)
                return True
        except Exception as e:
            print(f"❌ Error adding skin: {e}")
            return False
        
    async def get_tracked_skins(self):
        if not self.pool:
            await self.connect()
            
        query = "SELECT skin_name FROM tracked_items"
        try:
            async with self.pool.acquire() as connection:
                rows = await connection.fetch(query)
                return [row['skin_name'] for row in rows]
        except Exception as e:
            print(f"❌ Error fetching skin list: {e}")
            return []

    async def close(self):
        if self.pool:
            await self.pool.close()
            print("🔌 Database connection closed")

db = Database()