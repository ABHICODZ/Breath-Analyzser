import asyncio
from sqlalchemy import text
from app.db.database import engine
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_connection():
    """Verify that the FastAPI backend can connect to the Database."""
    try:
        async with engine.begin() as conn:
            # Check TimescaleDB extension
            result = await conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'timescaledb';"))
            ext = result.scalar()
            if ext:
                logger.info("✅ Connection successful. TimescaleDB extension is active!")
            else:
                logger.warning("⚠️ Connected to Postgres, but TimescaleDB extension is NOT installed/active.")
                
            # Check if our hypertable from init.sql exists
            result = await conn.execute(text("SELECT hypertable_name FROM timescaledb_information.hypertables WHERE hypertable_name = 'air_quality_data';"))
            hypertable = result.scalar()
            if hypertable:
                 logger.info("✅ Hypertable 'air_quality_data' found and ready.")
            else:
                 logger.error("❌ Hypertable not found. Did you run app/db/init.sql?")
                 
    except Exception as e:
        logger.error(f"❌ Database connection failed. Ensure PostgreSQL is running on {settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}")
        logger.error(f"Error details: {e}")

if __name__ == "__main__":
    asyncio.run(verify_connection())
