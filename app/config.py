from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://claims_user:claims_pass@localhost:5432/claims_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # JWT
    JWT_SECRET_KEY: str = "your-secret-key-change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 1
    JWT_REFRESH_EXPIRATION_DAYS: int = 7

    # Email Configuration
    SMTP_HOST: str = "smtp.office365.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "claimchaser@maximizedrevenue.com"
    SMTP_PASSWORD: str = ""  # Set via environment variable
    SMTP_FROM_EMAIL: str = "claimchaser@maximizedrevenue.com"
    SMTP_FROM_NAME: str = "Claim Chaser - Maximized Revenue"

    # Invitation
    INVITATION_TOKEN_EXPIRATION_HOURS: int = 48
    FRONTEND_URL: str = "http://localhost:5173"

    # App
    APP_NAME: str = "Claim Chaser API"
    DEBUG: bool = True
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    CORS_ALLOW_ORIGIN_REGEX: str = r"https://.*\.azurewebsites\.net|http://localhost:.*|http://127\.0\.0\.1:.*"

    # Default admin seeding
    DEFAULT_ADMIN_EMAIL: str = "claimchaser@maximizedrevenue.com"
    DEFAULT_ADMIN_PASSWORD: str = ""
    DEFAULT_ADMIN_FULL_NAME: str = "CC Admin"

    # Default user seeding
    DEFAULT_USER_EMAIL: str = "user1@gmail.com"
    DEFAULT_USER_PASSWORD: str = ""
    DEFAULT_USER_FULL_NAME: str = "User One"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
