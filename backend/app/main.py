from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from contextlib import asynccontextmanager

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.utils.db_init import create_first_admin
from app.services.encryption import encryption_service
from app.routers import auth, public, users, members
from app.routers import unlock as unlock_router
from app.vault import vault_manager


def vault_mode_enabled() -> bool:
    """Vault mode is active when a .vault file exists and SECRET_KEY
    was not already provided via environment / .env."""
    return vault_manager.vault_exists() and not settings.SECRET_KEY


def initialize_app():
    """Create tables, seed first admin, and initialize encryption.
    Called at startup (direct mode) or after vault unlock."""
    if settings.ENCRYPTION_KEY:
        encryption_service.initialize(settings.ENCRYPTION_KEY)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        create_first_admin(db)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    if not vault_mode_enabled():
        # Direct mode: secrets already in env, start normally
        initialize_app()
    yield
    # Shutdown: cleanup if needed


class LockMiddleware(BaseHTTPMiddleware):
    """When vault mode is active and the vault is still locked,
    block all routes except /api/unlock and /api/health."""

    async def dispatch(self, request: Request, call_next):
        if not vault_mode_enabled() or vault_manager.is_unlocked:
            return await call_next(request)

        path = request.url.path
        if path in ("/api/unlock", "/api/health"):
            return await call_next(request)

        if path.startswith("/api/"):
            return JSONResponse(
                {"detail": "Application is locked. Visit /unlock to enter the master password."},
                status_code=503,
            )

        return JSONResponse(
            {"detail": "Application is locked. Visit /unlock to enter the master password."},
            status_code=503,
        )


app = FastAPI(
    title="Membership Portal API",
    description="Secure membership application portal with field-level PII encryption",
    version="1.0.0",
    lifespan=lifespan
)

# Middleware order: CORS runs outermost, then LockMiddleware
app.add_middleware(LockMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(unlock_router.router, prefix="/api")
app.include_router(public.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(members.router, prefix="/api")


@app.get("/api/health")
def health_check():
    """Health check endpoint for Docker healthcheck."""
    if vault_mode_enabled() and not vault_manager.is_unlocked:
        return {"status": "locked"}
    return {"status": "healthy"}


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "Membership Portal API",
        "version": "1.0.0",
        "docs": "/docs"
    }
