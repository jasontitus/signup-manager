import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from app.models.user import User, UserRole
from app.models.member import Member, MemberStatus
from app.services.auth import hash_password

# Setup test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


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
    member1 = Member(
        first_name="John",
        last_name="Doe",
        street_address="123 Main St",
        phone_number="555-0001",
        email="john@example.com",
        branch_of_service="Army",
        rank="Sergeant",
        years_of_service="5",
        currently_serving=True,
        status=MemberStatus.ASSIGNED,
        assigned_vetter_id=vetter1.id
    )

    member2 = Member(
        first_name="Jane",
        last_name="Smith",
        street_address="456 Oak Ave",
        phone_number="555-0002",
        email="jane@example.com",
        branch_of_service="Navy",
        rank="Lieutenant",
        years_of_service="8",
        currently_serving=True,
        status=MemberStatus.ASSIGNED,
        assigned_vetter_id=vetter2.id
    )

    db.add(member1)
    db.add(member2)
    db.commit()

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
    response = client.post("/api/v1/auth/login", json={
        "username": "vetter1",
        "password": "password123"
    })
    assert response.status_code == 200
    token1 = response.json()["access_token"]

    # Try to access member2 (assigned to vetter2)
    response = client.get(
        f"/api/v1/members/{data['member2_id']}",
        headers={"Authorization": f"Bearer {token1}"}
    )

    # Should be forbidden
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()


def test_vetter_list_only_shows_assigned_members(setup_test_data):
    """CRITICAL: Test that list endpoint filters correctly for vetters."""
    data = setup_test_data

    # Login as vetter1
    response = client.post("/api/v1/auth/login", json={
        "username": "vetter1",
        "password": "password123"
    })
    assert response.status_code == 200
    token1 = response.json()["access_token"]

    # Get member list
    response = client.get(
        "/api/v1/members",
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
    response = client.post("/api/v1/auth/login", json={
        "username": "vetter1",
        "password": "password123"
    })
    assert response.status_code == 200
    token1 = response.json()["access_token"]

    # Access member1 (assigned to vetter1)
    response = client.get(
        f"/api/v1/members/{data['member1_id']}",
        headers={"Authorization": f"Bearer {token1}"}
    )

    assert response.status_code == 200
    member = response.json()
    assert member["id"] == data["member1_id"]
    assert member["first_name"] == "John"
