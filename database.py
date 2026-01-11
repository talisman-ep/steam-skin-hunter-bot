import asyncpg
from config import DB_HOST, DB_NAME, DB_PASS, DB_PORT, DB_USER

class Database():
    def __init__(self):
        self.pool = None
        
    async def connect(self):
        if not self.pool:
            print("Connecting to database...")
            try:
                self.pool = await asyncpg.create_pool(
                    user=DB_USER,
                    password=DB_PASS,
                    database=DB_NAME,
                    host=DB_HOST,
                    port=DB_PORT
                )
                print("Database connected successfully!")
            except Exception as e:
                print(f"Connection error: {e}")
            
    async def add_price(self, skin_name: str, price: float):
        if not self.pool:
            await self.connect()

        query = "INSERT INTO skin_prices (skin_name, price) VALUES ($1, $2)"
        try:
            async with self.pool.acquire() as connection:
                await connection.execute(query, skin_name, price)
        except Exception as e:
            print(f"Database write error: {e}")
            
    async def create_tables(self):
        """Creates tables and updates the structure if necessary"""
        if not self.pool:
            await self.connect()

        query_prices = """
        CREATE TABLE IF NOT EXISTS skin_prices (
            id SERIAL PRIMARY KEY,
            skin_name TEXT NOT NULL,
            price DOUBLE PRECISION NOT NULL,
            currency TEXT DEFAULT 'USD',
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        query_items = """
        CREATE TABLE IF NOT EXISTS tracked_items (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            skin_name TEXT NOT NULL,
            buy_price DOUBLE PRECISION,
            UNIQUE (user_id, skin_name)
        );
        """

        query_alter = """
        DO $$ 
        BEGIN 
            BEGIN
                ALTER TABLE tracked_items ADD COLUMN target_price DOUBLE PRECISION;
            EXCEPTION
                WHEN duplicate_column THEN RAISE NOTICE 'column target_price already exists in tracked_items.';
            END;
        END $$;
        """
        
        try:
            async with self.pool.acquire() as connection:
                await connection.execute(query_prices)
                await connection.execute(query_items)
                await connection.execute(query_alter)
                print("Tables checked/updated successfully")
        except Exception as e:
            print(f"Error creating tables: {e}")
            
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
            print(f"Database read error: {e}")
            return []

    async def add_track_skin(self, user_id: int, skin_name: str, buy_price: float = None):
        if not self.pool:
            await self.connect()

        query = """
            INSERT INTO tracked_items (user_id, skin_name, buy_price) 
            VALUES ($1, $2, $3) 
            ON CONFLICT (user_id, skin_name) 
            DO UPDATE SET buy_price = COALESCE($3, tracked_items.buy_price)
        """
        try:
            async with self.pool.acquire() as connection:
                await connection.execute(query, user_id, skin_name, buy_price)
                return True
        except Exception as e:
            print(f"Error adding skin: {e}")
            return False

    async def set_alert_price(self, user_id, skin_name, target_price):
        """Sets the price for notification"""
        if not self.pool: await self.connect()
        query = """
        UPDATE tracked_items 
        SET target_price = $3 
        WHERE user_id = $1 AND skin_name = $2
        """
        try:
            async with self.pool.acquire() as connection:
                result = await connection.execute(query, user_id, skin_name, float(target_price))
                return "UPDATE" in result
        except Exception as e:
            print(f"Error setting alert: {e}")
            return False

    async def get_all_alerts(self):
        """Returns all active notifications (where target_price is not empty)"""
        if not self.pool: await self.connect()
        query = "SELECT user_id, skin_name, target_price FROM tracked_items WHERE target_price IS NOT NULL"
        async with self.pool.acquire() as connection:
            return await connection.fetch(query)

    async def remove_alert(self, user_id, skin_name):
        """Removes the notification (resets target_price)"""
        if not self.pool: await self.connect()
        query = "UPDATE tracked_items SET target_price = NULL WHERE user_id = $1 AND skin_name = $2"
        async with self.pool.acquire() as connection:
            await connection.execute(query, user_id, skin_name)

    async def get_user_items(self, user_id: int):
        """Returns skins ONLY for a specific user (updated: added target_price)"""
        if not self.pool:
            await self.connect()

        query = "SELECT skin_name, buy_price, target_price FROM tracked_items WHERE user_id = $1"
        try:
            async with self.pool.acquire() as connection:
                rows = await connection.fetch(query, user_id)
                return rows 
        except Exception as e:
            print(f"Error fetching user items: {e}")
            return []

    async def delete_track_skin(self, user_id: int, skin_name: str):
        """Removes the skin for a specific user"""
        if not self.pool:
            await self.connect()
            
        query = "DELETE FROM tracked_items WHERE user_id = $1 AND skin_name = $2"
        try:
            async with self.pool.acquire() as connection:
                result = await connection.execute(query, user_id, skin_name)
                if "DELETE 0" in result:
                    return False
                return True
        except Exception as e:
            print(f"Error deleting skin: {e}")
            return False

    async def get_all_unique_skins(self):
        """Returns a list of all unique names (without duplicates) for parsing"""
        if not self.pool:
            await self.connect()
        
        query = "SELECT DISTINCT skin_name FROM tracked_items"
        try:
            async with self.pool.acquire() as connection:
                rows = await connection.fetch(query)
                return rows 
        except Exception as e:
            print(f"Error fetching unique skins: {e}")
            return []

    async def close(self):
        if self.pool:
            await self.pool.close()
            print("Database connection closed")

db = Database()