from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    print(f"🚀 Starting {settings.app_name}...")
    await init_db()
    print("✅ Database ready")

    # Start background sync scheduler
    from app.tasks.scheduler import start_scheduler
    scheduler = start_scheduler()
    print(f"⏰ Sync scheduler started (every {settings.sync_interval_minutes}m)")

    yield

    # Shutdown
    scheduler.shutdown()
    print("👋 Scheduler stopped")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/api/docs" if settings.is_development else None,
    redoc_url=None,
    lifespan=lifespan,
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────
from app.api.v1.endpoints import auth, activities, sleep, nutrition, analytics, profile  # noqa: E402

app.include_router(auth.router,       prefix="/api/v1/auth",       tags=["auth"])
app.include_router(activities.router, prefix="/api/v1/activities", tags=["activities"])
app.include_router(sleep.router,      prefix="/api/v1/sleep",      tags=["sleep"])
app.include_router(nutrition.router,  prefix="/api/v1/nutrition",  tags=["nutrition"])
app.include_router(analytics.router,  prefix="/api/v1/analytics",  tags=["analytics"])
app.include_router(profile.router,    prefix="/api/v1/profile",    tags=["profile"])


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": settings.app_name}
