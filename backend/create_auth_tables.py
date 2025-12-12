import asyncio
from db import engine, Base

async def init_models():
    print("Creating Auth tables (Users)...")
    async with engine.begin() as conn:
        # This looks at your 'User' class in db.py and generates the correct SQL
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Users table created successfully.")

if __name__ == "__main__":
    asyncio.run(init_models())