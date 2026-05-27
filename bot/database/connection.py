from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from bot.config import settings


# ── Async Engine ──────────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.database_url,
    echo=False,          # True qilsangiz SQL loglarni ko'rasiz
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

# ── Session Factory ───────────────────────────────────────────────────────────
AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ── Base Model ────────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncSession:
    """Dependency: database session olish"""
    async with AsyncSessionFactory() as session:
        yield session


async def create_all_tables():
    """Development uchun — production'da alembic ishlatiladi"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Bot o'chganda connection pool yopish"""
    await engine.dispose()
