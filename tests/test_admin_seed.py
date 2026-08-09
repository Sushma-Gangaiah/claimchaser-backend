import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select

from app.db.base import Base
from app.models import User, UserRole
from app.services.bootstrap import ensure_default_admin
from app.utils.auth import verify_password


def test_ensure_default_admin_creates_admin_user():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _run_test():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as db:
            user = await ensure_default_admin(
                db,
                email="seed-test@example.com",
                password="SeedPass123!",
                full_name="Seeded Admin",
            )

            assert user is not None
            assert user.email == "seed-test@example.com"
            assert user.role == UserRole.ADMIN
            assert user.password_set is True

            stmt = select(User).where(User.email == "seed-test@example.com")
            result = await db.execute(stmt)
            persisted = result.scalars().first()

            assert persisted is not None
            assert verify_password("SeedPass123!", persisted.password_hash)

        await engine.dispose()

    asyncio.run(_run_test())
