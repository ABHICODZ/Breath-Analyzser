from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# Create async SQLAlchemy engine
engine = create_async_engine(
    settings.async_database_url,
    echo=True, # Set to False in production
    future=True
)

# Create session factory
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

async def get_db():
    """Dependency for getting async database sessions"""
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
