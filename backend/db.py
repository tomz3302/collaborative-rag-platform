from typing import AsyncGenerator
from fastapi import Depends
from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable, SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import Column, String, Integer, Boolean
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# -------------------------------------------------------------------------
# DATABASE CONFIGURATION (Supabase/PostgreSQL)
# Loaded from .env file
# -------------------------------------------------------------------------
DB_HOST = os.getenv('POSTGRES_HOST')
DB_NAME = os.getenv('POSTGRES_DATABASE', 'postgres')
DB_USER = os.getenv('POSTGRES_USER')
DB_PASS = os.getenv('POSTGRES_PASSWORD')
DB_PORT = int(os.getenv('POSTGRES_PORT', 6543))

# Connection String for SQLAlchemy (Async) - PostgreSQL with SSL for Supabase
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}?ssl=require"

class Base(DeclarativeBase):
    pass

# This defines the 'users' table structure for SQLAlchemy
class User(SQLAlchemyBaseUserTable[int], Base):
    id = Column(Integer, primary_key=True)
    full_name = Column(String(length=100), nullable=True)
    # The library automatically adds: email, hashed_password, is_active, etc.

engine = create_async_engine(
    DATABASE_URL,
    connect_args={
        "prepared_statement_cache_size": 0,  # Disables prepared statements
        "statement_cache_size": 0,           # Ensures no caching happens
    }
)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session

async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)