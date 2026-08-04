"""FastAPI main application with improved middleware and error handling."""
import time
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path

from app.core.config import settings
from app.api.router import api_router

# ── Logging ──
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s" if settings.LOG_FORMAT == "text"
    else '{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","message":"%(message)s"}',
)
logger = logging.getLogger(__name__)

# ── App ──
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/api/docs" if not settings.is_production else None,
    redoc_url="/api/redoc" if not settings.is_production else None,
    openapi_url="/api/openapi.json" if not settings.is_production else None,
)

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# ── Request logging & timing middleware ──
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration = (time.perf_counter() - start) * 1000
    # Don't log health checks in production
    if not (settings.is_production and request.url.path == "/health"):
        logger.info(
            f"{request.method} {request.url.path} "
            f"→ {response.status_code} ({duration:.1f}ms) "
            f"[{request.client.host if request.client else 'unknown'}]"
        )
    return response


# ── Exception handlers ──
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误" if settings.is_production else str(exc)},
    )


# ── Routes ──
app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": settings.APP_VERSION, "timestamp": int(time.time())}


@app.get("/api/debug")
async def debug_info():
    """Debug endpoint (disabled in production)."""
    if settings.is_production:
        return {"status": "disabled", "message": "Debug disabled in production"}

    from app.core.database import AsyncSessionLocal, check_db_health
    from sqlalchemy import text

    info = {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "db_url_prefix": settings.async_database_url[:40] + "...",
        "secret_key_set": settings.SECRET_KEY != "your-secret-key-change-in-production",
    }

    db_health = await check_db_health()
    info["database"] = db_health

    return info


@app.get("/api/init")
async def init_database():
    """One-time DB initialization: create tables + admin user."""
    from app.core.database import engine, AsyncSessionLocal
    from app.core.security import get_password_hash
    from app.models.models import User, Base
    from sqlalchemy import select

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.username == "admin")
        )
        admin = result.scalar_one_or_none()
        if not admin:
            admin = User(
                username="admin",
                password_hash=get_password_hash("admin123"),
                real_name="超级管理员",
                phone="13800000000",
                role="admin",
                team="管理层",
                commission_rate=0.0,
                is_active=True,
            )
            session.add(admin)
            await session.commit()
            return {"status": "ok", "message": "Tables created + admin created (admin/admin123)"}
        return {"status": "ok", "message": "Tables already exist, admin exists"}


# ── Static files (frontend SPA) ──
FRONTEND_DIR = Path(__file__).parent.parent / "static"

if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(request: Request, full_path: str):
        """Serve frontend SPA (catch-all for Vue Router history mode)."""
        # Skip API routes
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Not found"})

        file_path = FRONTEND_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIR / "index.html")
