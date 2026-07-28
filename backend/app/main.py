import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.api.router import api_router

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)

cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/api/debug")
async def debug_info():
    """Debug endpoint to check DB connectivity and config."""
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import text
    info = {
        "db_url_prefix": settings.async_database_url[:40] + "...",
        "secret_key_set": settings.SECRET_KEY != "your-secret-key-change-in-production",
        "cors": settings.CORS_ORIGINS,
    }
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT COUNT(*) FROM users"))
            count = result.scalar()
            info["db_connected"] = True
            info["users_count"] = count
    except Exception as e:
        info["db_connected"] = False
        info["db_error"] = f"{type(e).__name__}: {str(e)}"
    return info


@app.get("/api/init")
async def init_database():
    """One-time init: create tables + admin user."""
    from app.core.database import engine, AsyncSessionLocal
    from app.core.security import get_password_hash
    from app.models.user import User, Base, UserRole
    from app.models.product import Product
    from app.models.customer import Customer
    from app.models.order import Order, Shipment, AfterSales
    from sqlalchemy import select

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create admin user
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.username == "admin"))
        admin = result.scalar_one_or_none()
        if not admin:
            admin = User(
                username="admin",
                password_hash=get_password_hash("admin123"),
                real_name="超级管理员",
                phone="13800000000",
                role=UserRole.admin,
                team="管理层",
                commission_rate=0.0,
                is_active=True,
            )
            session.add(admin)
            await session.commit()
            return {"status": "ok", "message": "Tables created + admin user created"}
        return {"status": "ok", "message": "Tables created, admin already exists"}


# Serve frontend static files (for single-service deployment)
FRONTEND_DIR = Path(__file__).parent.parent / "static"

if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(request: Request, full_path: str):
        """Serve frontend for all non-API routes (Vue Router history mode)."""
        file_path = FRONTEND_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIR / "index.html")
