from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from app.services.auth import hash_password
from app.config import settings


def create_first_admin(db: Session) -> None:
    """Create the first admin user if it doesn't exist (first run only)."""
    if not settings.FIRST_RUN_ADMIN_USER or not settings.FIRST_RUN_ADMIN_PASSWORD:
        print("FIRST_RUN_ADMIN_USER or FIRST_RUN_ADMIN_PASSWORD not set, skipping admin creation")
        return

    # Check if admin already exists
    existing_admin = db.query(User).filter(User.username == settings.FIRST_RUN_ADMIN_USER).first()
    if existing_admin:
        print(f"Admin user '{settings.FIRST_RUN_ADMIN_USER}' already exists, skipping creation")
        return

    # Create admin user
    admin = User(
        username=settings.FIRST_RUN_ADMIN_USER,
        hashed_password=hash_password(settings.FIRST_RUN_ADMIN_PASSWORD),
        role=UserRole.SUPER_ADMIN,
        full_name="System Administrator",
        is_active=True
    )
    db.add(admin)
    db.commit()
    print(f"Created first admin user: {settings.FIRST_RUN_ADMIN_USER}")
