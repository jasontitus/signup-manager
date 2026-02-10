"""
Shared test fixtures for the Signup Manager test suite.

Provides:
- Test database (SQLite in-memory)
- Encryption service initialization
- Reusable fixtures for admin, vetter, and member creation
- Auth helper to get JWT tokens
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app, initialize_app
from app.database import Base, get_db
from app.models.user import User, UserRole
from app.models.member import Member, MemberStatus
from app.models.audit_log import AuditLog
from app.services.auth import hash_password
from app.services.encryption import encryption_service
from app.config import settings

# ---------------------------------------------------------------------------
# Database & encryption setup
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite:///./test_suite.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Ensure encryption is initialized for tests
_TEST_KEY = "UJiLdEHqngyMSWzs4a70Y11rQ70faKLG4AdNo-PW0GM="  # Valid Fernet key for tests
if not settings.ENCRYPTION_KEY:
    # Set a test key if none is configured
    object.__setattr__(settings, "ENCRYPTION_KEY", _TEST_KEY)
    object.__setattr__(settings, "SECRET_KEY", "test-secret-key-for-jwt-signing-only")
    object.__setattr__(settings, "EMAIL_BLIND_INDEX_SALT", "test-salt-for-blind-index")

try:
    encryption_service.initialize(settings.ENCRYPTION_KEY)
except Exception:
    pass  # Already initialized


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Create all tables once for the test session."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def clean_tables():
    """Clean all rows between tests for isolation."""
    yield
    db = TestSession()
    db.query(AuditLog).delete()
    db.query(Member).delete()
    db.query(User).delete()
    db.commit()
    db.close()


@pytest.fixture
def db():
    """Provide a test database session."""
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    """Provide a test HTTP client."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# User factory fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def admin_user(db):
    """Create and return an admin user."""
    user = User(
        username="admin",
        hashed_password=hash_password("admin-password"),
        role=UserRole.SUPER_ADMIN,
        full_name="Test Admin",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def vetter_user(db):
    """Create and return a vetter user."""
    user = User(
        username="vetter1",
        hashed_password=hash_password("vetter-password"),
        role=UserRole.VETTER,
        full_name="Test Vetter",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def vetter_user2(db):
    """Create and return a second vetter user."""
    user = User(
        username="vetter2",
        hashed_password=hash_password("vetter-password"),
        role=UserRole.VETTER,
        full_name="Test Vetter Two",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def inactive_user(db):
    """Create and return an inactive user."""
    user = User(
        username="inactive",
        hashed_password=hash_password("inactive-password"),
        role=UserRole.VETTER,
        full_name="Inactive User",
        is_active=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Member factory
# ---------------------------------------------------------------------------

def make_member(
    db,
    first_name="John",
    last_name="Doe",
    city="Springfield",
    zip_code="62701",
    email="john@example.com",
    status=MemberStatus.PENDING,
    assigned_vetter_id=None,
):
    """Create a member with all encrypted fields set via hybrid properties."""
    member = Member(status=status, assigned_vetter_id=assigned_vetter_id)
    member.first_name = first_name
    member.last_name = last_name
    member.city = city
    member.zip_code = zip_code
    member.street_address = "123 Test St"
    member.phone_number = "555-0000"
    member.email = email
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@pytest.fixture
def pending_member(db):
    """Create a pending member."""
    return make_member(db)


@pytest.fixture
def assigned_member(db, vetter_user):
    """Create a member assigned to vetter_user."""
    return make_member(
        db,
        first_name="Jane",
        last_name="Smith",
        email="jane@example.com",
        status=MemberStatus.ASSIGNED,
        assigned_vetter_id=vetter_user.id,
    )


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def login(client, username, password):
    """Log in and return the JWT token."""
    resp = client.post("/api/auth/login", json={
        "username": username,
        "password": password,
    })
    assert resp.status_code == 200, f"Login failed: {resp.json()}"
    return resp.json()["access_token"]


def auth_header(token):
    """Return an Authorization header dict."""
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_token(client, admin_user):
    """Return a valid admin JWT token."""
    return login(client, "admin", "admin-password")


@pytest.fixture
def vetter_token(client, vetter_user):
    """Return a valid vetter JWT token."""
    return login(client, "vetter1", "vetter-password")


@pytest.fixture
def vetter2_token(client, vetter_user2):
    """Return a valid second vetter JWT token."""
    return login(client, "vetter2", "vetter-password")
