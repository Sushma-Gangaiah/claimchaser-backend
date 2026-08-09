import asyncio
from app.db.session import async_session
from app.services.bootstrap import ensure_default_admin, ensure_default_user
from app.db.base import Base
from app.db.session import engine


async def init_db():
    """Initialize database and create default admin user."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        await ensure_default_admin(session)
        await ensure_default_user(session)
        print("✓ Database initialized successfully")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_db())
