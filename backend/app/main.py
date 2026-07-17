import asyncio
import logging

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
from app.routers import auth, public, users, members, tags
from app.routers import unlock as unlock_router
from app.vault import vault_manager


def vault_mode_enabled() -> bool:
    """Vault mode is active when a .vault file exists and SECRET_KEY
    was not already provided via environment / .env."""
    return vault_manager.vault_exists() and not settings.SECRET_KEY


def run_migrations(db_engine):
    """Add new columns to existing tables if they don't exist.
    SQLAlchemy's create_all only creates new tables, not new columns."""
    from sqlalchemy import inspect, text
    inspector = inspect(db_engine)

    if "members" in inspector.get_table_names():
        existing_cols = {col["name"] for col in inspector.get_columns("members")}

        with db_engine.connect() as conn:
            if "processing_completed" not in existing_cols:
                conn.execute(text(
                    "ALTER TABLE members ADD COLUMN processing_completed BOOLEAN NOT NULL DEFAULT 0"
                ))
                conn.commit()
                print("Migration: added 'processing_completed' column to members table")

            if "tags" not in existing_cols:
                conn.execute(text(
                    "ALTER TABLE members ADD COLUMN tags TEXT"
                ))
                conn.commit()
                print("Migration: added 'tags' column to members table")

            # --- Status enum cleanup migration ---
            # Step 1: Add archived column if not exists
            if "archived" not in existing_cols:
                conn.execute(text(
                    "ALTER TABLE members ADD COLUMN archived BOOLEAN NOT NULL DEFAULT 0"
                ))
                conn.commit()
                print("Migration: added 'archived' column to members table")

            # Step 2: Set archived=True for members with status=ARCHIVED
            result = conn.execute(text(
                "UPDATE members SET archived = 1 WHERE status = 'ARCHIVED' AND archived = 0"
            ))
            conn.commit()
            if result.rowcount > 0:
                print(f"Migration: marked {result.rowcount} ARCHIVED members as archived=True")

            # Step 3: Update status ARCHIVED → IN_SIGNAL (formerly PROCESSED)
            result = conn.execute(text(
                "UPDATE members SET status = 'IN_SIGNAL' WHERE status = 'ARCHIVED'"
            ))
            conn.commit()
            if result.rowcount > 0:
                print(f"Migration: changed {result.rowcount} ARCHIVED → IN_SIGNAL")

            # Step 4: Update status to IN_SIGNAL for processing_completed=True members
            if "processing_completed" in existing_cols:
                result = conn.execute(text(
                    "UPDATE members SET status = 'IN_SIGNAL' WHERE processing_completed = 1 AND status NOT IN ('IN_SIGNAL', 'PROCESSED')"
                ))
                conn.commit()
                if result.rowcount > 0:
                    print(f"Migration: changed {result.rowcount} processing_completed → IN_SIGNAL")

            # --- Status rename migration (June 2026) ---
            # PROCESSED renamed to IN_SIGNAL; UNSURE removed (folded into NEEDS_FOLLOW_UP)
            result = conn.execute(text(
                "UPDATE members SET status = 'IN_SIGNAL' WHERE status = 'PROCESSED'"
            ))
            conn.commit()
            if result.rowcount > 0:
                print(f"Migration: changed {result.rowcount} PROCESSED → IN_SIGNAL")

            result = conn.execute(text(
                "UPDATE members SET status = 'NEEDS_FOLLOW_UP' WHERE status = 'UNSURE'"
            ))
            conn.commit()
            if result.rowcount > 0:
                print(f"Migration: changed {result.rowcount} UNSURE → NEEDS_FOLLOW_UP")

            # --- Follow-up scheduling columns ---
            if "vetted_at" not in existing_cols:
                conn.execute(text("ALTER TABLE members ADD COLUMN vetted_at DATETIME"))
                conn.commit()
                print("Migration: added 'vetted_at' column to members table")
                # Backfill: existing VETTED members anchor their one-month
                # timer to their last update (best available estimate)
                conn.execute(text(
                    "UPDATE members SET vetted_at = updated_at WHERE status = 'VETTED' AND vetted_at IS NULL"
                ))
                conn.commit()

            if "resting_since" not in existing_cols:
                conn.execute(text("ALTER TABLE members ADD COLUMN resting_since DATETIME"))
                conn.commit()
                print("Migration: added 'resting_since' column to members table")
                # Backfill: existing IN_SIGNAL members anchor their six-month
                # timer to their last update
                conn.execute(text(
                    "UPDATE members SET resting_since = updated_at WHERE status = 'IN_SIGNAL' AND resting_since IS NULL"
                ))
                conn.commit()

            if "one_month_followup_sent" not in existing_cols:
                conn.execute(text(
                    "ALTER TABLE members ADD COLUMN one_month_followup_sent BOOLEAN NOT NULL DEFAULT 0"
                ))
                conn.commit()
                print("Migration: added 'one_month_followup_sent' column to members table")
                # Don't retroactively ping the historical backlog: members
                # vetted more than 30 days before this migration are exempted
                # from the one-month follow-up. New vettings get the full flow.
                result = conn.execute(text(
                    "UPDATE members SET one_month_followup_sent = 1 "
                    "WHERE status = 'VETTED' AND updated_at <= datetime('now', '-30 days')"
                ))
                conn.commit()
                if result.rowcount > 0:
                    print(f"Migration: exempted {result.rowcount} previously-vetted members from one-month follow-up")


def validate_secrets():
    """Refuse to start with missing security-critical secrets.
    An empty SECRET_KEY would make every JWT forgeable; an empty
    ENCRYPTION_KEY / blind-index salt silently degrades PII protection."""
    missing = [
        name for name in ("SECRET_KEY", "ENCRYPTION_KEY", "EMAIL_BLIND_INDEX_SALT")
        if not getattr(settings, name)
    ]
    if missing:
        raise RuntimeError(
            f"Refusing to start: missing required secrets: {', '.join(missing)}. "
            "Set them in .env (development) or create a vault with 'python vault.py create' (production)."
        )


def initialize_app():
    """Create tables, seed first admin, and initialize encryption.
    Called at startup (direct mode) or after vault unlock."""
    validate_secrets()
    encryption_service.initialize(settings.ENCRYPTION_KEY)
    Base.metadata.create_all(bind=engine)
    run_migrations(engine)
    db = SessionLocal()
    try:
        create_first_admin(db)
    finally:
        db.close()


FOLLOWUP_CHECK_INTERVAL_SECONDS = 3600  # hourly


async def followup_scheduler():
    """Periodically run follow-up checks (one-month and six-month pings).
    Skips runs while the vault is locked (PII cannot be decrypted)."""
    from app.services.followups import run_followup_checks
    logger = logging.getLogger(__name__)
    while True:
        try:
            if not (vault_mode_enabled() and not vault_manager.is_unlocked):
                await asyncio.to_thread(run_followup_checks)
        except Exception:
            logger.exception("Follow-up check failed")
        await asyncio.sleep(FOLLOWUP_CHECK_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    if not vault_mode_enabled():
        # Direct mode: secrets already in env, start normally
        initialize_app()
    scheduler_task = asyncio.create_task(followup_scheduler())
    yield
    # Shutdown: cleanup
    scheduler_task.cancel()


class LockMiddleware(BaseHTTPMiddleware):
    """When vault mode is active and the vault is still locked,
    block all routes except /api/unlock and /api/health."""

    async def dispatch(self, request: Request, call_next):
        if not vault_mode_enabled() or vault_manager.is_unlocked:
            return await call_next(request)

        if request.url.path in ("/api/unlock", "/api/health"):
            return await call_next(request)

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
app.include_router(tags.router, prefix="/api")


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
