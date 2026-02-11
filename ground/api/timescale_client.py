from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

DATABASE_URL = "postgresql+asyncpg://postgres:space@localhost:5432/space"

engine = create_async_engine(DATABASE_URL, pool_size=10, max_overflow=20)
SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)


async def get_timescale_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


