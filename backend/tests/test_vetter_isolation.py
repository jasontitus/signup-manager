import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from app.models.user import User, UserRole
from app.models.member import Member, MemberStatus
from app.services.auth import hash_password
from app.services.encryption import encryption_service
from app.config import settings

# Setup test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Initialize encryption for tests if not already done
if settings.ENCRYPTION_KEY:
    try:
        encryption_service.initialize(settings.ENCRYPTION_KEY)
    except Exception:
        pass  # Already initialized

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def create_test_member(first_name, last_name, city, zip_code, email, status, assigned_vetter_id):
    """Helper to create a Member with all encrypted fields set via hybrid properties."""
    member = Member(status=status, assigned_vetter_id=assigned_vetter_id)
    member.first_name = first_name
    member.last_name = last_name
    member.city = city
    member.zip_code = zip_code
    member.street_address = "123 Test St"
    member.phone_number = "555-0000"
    member.email = email
    return member


@pytest.fixture
def setup_test_data():
    """Create test users and members."""
    db = TestingSessionLocal()

    # Create two vetters
    vetter1 = User(
        username="vetter1",
        hashed_password=hash_password("password123"),
        role=UserRole.VETTER,
        full_name="Vetter One",
        is_active=True
    )
    vetter2 = User(
        username="vetter2",
        hashed_password=hash_password("password123"),
        role=UserRole.VETTER,
        full_name="Vetter Two",
        is_active=True
    )

    db.add(vetter1)
    db.add(vetter2)
    db.commit()
    db.refresh(vetter1)
    db.refresh(vetter2)

    # Create two members, one assigned to each vetter
    member1 = create_test_member(
        first_name="John", last_name="Doe",
        city="Springfield", zip_code="62701",
        email="john@example.com",
        status=MemberStatus.ASSIGNED,
        assigned_vetter_id=vetter1.id
    )
    member2 = create_test_member(
        first_name="Jane", last_name="Smith",
        city="Shelbyville", zip_code="62702",
        email="jane@example.com",
        status=MemberStatus.ASSIGNED,
        assigned_vetter_id=vetter2.id
    )

    db.add(member1)
    db.add(member2)
    db.commit()
    db.refresh(member1)
    db.refresh(member2)

    yield {
        "vetter1_id": vetter1.id,
        "vetter2_id": vetter2.id,
        "member1_id": member1.id,
        "member2_id": member2.id
    }

    # Cleanup
    db.query(Member).delete()
    db.query(User).delete()
    db.commit()
    db.close()


def test_vetter_cannot_access_other_vetter_member(setup_test_data):
    """CRITICAL: Test that vetter A cannot access vetter B's member."""
    data = setup_test_data

    # Login as vetter1
    response = client.post("/api/auth/login", json={
        "username": "vetter1",
        "password": "password123"
    })
    assert response.status_code == 200
    token1 = response.json()["access_token"]

    # Try to access member2 (assigned to vetter2)
    response = client.get(
        f"/api/members/{data['member2_id']}",
        headers={"Authorization": f"Bearer {token1}"}
    )

    # Should be forbidden
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()


def test_vetter_list_only_shows_assigned_members(setup_test_data):
    """CRITICAL: Test that list endpoint filters correctly for vetters."""
    data = setup_test_data

    # Login as vetter1
    response = client.post("/api/auth/login", json={
        "username": "vetter1",
        "password": "password123"
    })
    assert response.status_code == 200
    token1 = response.json()["access_token"]

    # Get member list
    response = client.get(
        "/api/members",
        headers={"Authorization": f"Bearer {token1}"}
    )

    assert response.status_code == 200
    members = response.json()

    # Should only see member1
    assert len(members) == 1
    assert members[0]["id"] == data["member1_id"]


def test_vetter_can_access_assigned_member(setup_test_data):
    """Test that vetter can access their assigned member."""
    data = setup_test_data

    # Login as vetter1
    response = client.post("/api/auth/login", json={
        "username": "vetter1",
        "password": "password123"
    })
    assert response.status_code == 200
    token1 = response.json()["access_token"]

    # Access member1 (assigned to vetter1)
    response = client.get(
        f"/api/members/{data['member1_id']}",
        headers={"Authorization": f"Bearer {token1}"}
    )

    assert response.status_code == 200
    member = response.json()
    assert member["id"] == data["member1_id"]
    assert member["first_name"] == "John"
