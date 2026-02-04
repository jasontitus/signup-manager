from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.database import engine, Base, SessionLocal
from app.utils.db_init import create_first_admin
from app.routers import auth, public, users, members


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup: Create tables and initialize first admin
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        create_first_admin(db)
    finally:
        db.close()
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="Membership Portal API",
    description="Secure membership application portal with field-level PII encryption",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(public.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(members.router, prefix="/api/v1")


@app.get("/api/v1/health")
def health_check():
    """Health check endpoint for Docker healthcheck."""
    return {"status": "healthy"}


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "Membership Portal API",
        "version": "1.0.0",
        "docs": "/docs"
    }
