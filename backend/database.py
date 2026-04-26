"""
Lead Engine — Database Setup
Async SQLite via SQLAlchemy for zero-config local persistence.
"""
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Use Environment Variable for production (e.g. Postgres on Supabase/Render)
# Default to local SQLite if no URL is provided
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Ensure the URL is in async format (e.g. postgresql+asyncpg://...)
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
else:
    # Local SQLite fallback
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lead_engine.db")
    DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

# Configure engine options
engine_args = {}
if DATABASE_URL.startswith("postgresql"):
    # Fix for Supabase/PgBouncer: "prepared statement already exists"
    # We disable the statement cache which PgBouncer doesn't support in transaction mode
    engine_args["connect_args"] = {"statement_cache_size": 0}

engine = create_async_engine(DATABASE_URL, echo=False, **engine_args)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    """FastAPI dependency — yields an async DB session."""
    async with async_session() as session:
        yield session


async def init_db():
    """Create all tables on startup."""
    from backend.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
