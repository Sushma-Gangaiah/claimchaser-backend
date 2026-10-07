from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import auth, admin, invitation, user
from app.db.base import Base
from app.db.migrations import ensure_entry_claims_number, ensure_entry_claim_due
from app.db.session import async_session, engine
from app.services.bootstrap import ensure_default_admin, ensure_default_user

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Claims tracking and management platform API",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ALLOW_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(invitation.router)
app.include_router(user.router)


@app.get("/", tags=["root"])
async def root():
    """Root endpoint"""
    return {"message": "Claim Chaser API", "version": "1.0.0"}


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.on_event("startup")
async def startup():
    """Initialize database and seed the default admin user on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(ensure_entry_claims_number)
        await conn.run_sync(ensure_entry_claim_due)

    async with async_session() as db:
        await ensure_default_admin(db)
        await ensure_default_user(db)

    print("Database initialized and default admin checked")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
