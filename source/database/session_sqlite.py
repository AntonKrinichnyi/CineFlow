from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from config.dependencies import get_settings 
from database.models.base import Base

settings = get_settings()

SQLITE_DATABASE_URL = settings.SQLITE_DB_URL
sqlite_engine = create_async_engine(SQLITE_DATABASE_URL, echo=False)
AsyncSQLiteSessionLocal = sessionmaker(
    bind=sqlite_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_sqlite_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSQLiteSessionLocal() as session:
        yield session


@asynccontextmanager
async def get_sqlite_db_contextmanager() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSQLiteSessionLocal() as session:
        yield session


async def reset_sqlite_database() -> None:
    async with sqlite_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
