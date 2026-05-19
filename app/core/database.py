from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

readonly_engine = create_async_engine(settings.readonly_database_url, echo=False)
readonly_session = async_sessionmaker(readonly_engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_readonly_db() -> AsyncSession:
    async with readonly_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
