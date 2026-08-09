from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config import settings
from app.models import User, UserRole
from app.utils.auth import hash_password


async def ensure_default_admin(
    db: AsyncSession,
    email: str | None = None,
    password: str | None = None,
    full_name: str | None = None,
) -> User:
    """Create the default admin user if it does not already exist."""
    email = email or settings.DEFAULT_ADMIN_EMAIL
    password = password or settings.DEFAULT_ADMIN_PASSWORD
    full_name = full_name or settings.DEFAULT_ADMIN_FULL_NAME

    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    admin = result.scalars().first()

    if admin is None:
        admin = User(
            email=email,
            full_name=full_name,
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            is_active=True,
            password_set=True,
        )
        db.add(admin)
        await db.commit()
        await db.refresh(admin)
        return admin

    return admin


async def ensure_default_user(
    db: AsyncSession,
    email: str | None = None,
    password: str | None = None,
    full_name: str | None = None,
) -> User:
    """Create a default regular user if it does not already exist."""
    email = email or settings.DEFAULT_USER_EMAIL
    password = password or settings.DEFAULT_USER_PASSWORD
    full_name = full_name or settings.DEFAULT_USER_FULL_NAME

    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if user is None:
        user = User(
            email=email,
            full_name=full_name,
            password_hash=hash_password(password),
            role=UserRole.USER,
            is_active=True,
            password_set=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    return user
