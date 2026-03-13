"""Tests for GROUP_ADMIN role — can manage members and vetters, but not admins."""

import pytest
from app.models.user import User, UserRole
from app.models.member import MemberStatus
from app.services.auth import hash_password
from tests.conftest import auth_header, login, make_member


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def group_admin(db):
    """Create and return a group admin user."""
    user = User(
        username="groupadmin",
        hashed_password=hash_password("groupadmin-password"),
        role=UserRole.GROUP_ADMIN,
        full_name="Test Group Admin",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def group_admin_token(client, group_admin):
    """Return a valid group admin JWT token."""
    return login(client, "groupadmin", "groupadmin-password")


# ---------------------------------------------------------------------------
# Login & redirect
# ---------------------------------------------------------------------------

def test_group_admin_can_login(client, group_admin):
    """GROUP_ADMIN can log in and receives correct role."""
    resp = client.post("/api/auth/login", json={
        "username": "groupadmin",
        "password": "groupadmin-password",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "GROUP_ADMIN"
    assert data["username"] == "groupadmin"


# ---------------------------------------------------------------------------
# Member access — GROUP_ADMIN sees all members (like SUPER_ADMIN)
# ---------------------------------------------------------------------------

def test_group_admin_sees_all_members(client, db, group_admin_token):
    """GROUP_ADMIN can list all members, not just assigned ones."""
    m1 = make_member(db, first_name="Alice", email="alice@example.com")
    m2 = make_member(db, first_name="Bob", email="bob@example.com",
                     status=MemberStatus.ASSIGNED, assigned_vetter_id=999)
    resp = client.get("/api/members", headers=auth_header(group_admin_token))
    assert resp.status_code == 200
    ids = {m["id"] for m in resp.json()}
    assert m1.id in ids
    assert m2.id in ids


def test_group_admin_can_view_member_detail(client, db, group_admin_token):
    """GROUP_ADMIN can view any member's detail (decrypted PII)."""
    member = make_member(db)
    resp = client.get(f"/api/members/{member.id}",
                      headers=auth_header(group_admin_token))
    assert resp.status_code == 200
    assert resp.json()["first_name"] == "John"


def test_group_admin_can_update_member_status(client, db, group_admin_token):
    """GROUP_ADMIN can change a member's status."""
    member = make_member(db, status=MemberStatus.PENDING)
    resp = client.patch(
        f"/api/members/{member.id}/status",
        headers=auth_header(group_admin_token),
        json={"status": "PROCESSED"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "PROCESSED"


def test_group_admin_can_add_notes(client, db, group_admin_token):
    """GROUP_ADMIN can add notes to any member."""
    member = make_member(db)
    resp = client.post(
        f"/api/members/{member.id}/notes",
        headers=auth_header(group_admin_token),
        json={"note": "Reviewed by group admin"},
    )
    assert resp.status_code == 200
    assert "Reviewed by group admin" in resp.json()["notes"]


def test_group_admin_can_search_members(client, db, group_admin_token):
    """GROUP_ADMIN can search across all members."""
    make_member(db, first_name="Unique", email="unique@example.com")
    resp = client.get("/api/members/search/query?q=Unique",
                      headers=auth_header(group_admin_token))
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_group_admin_can_view_contacts(client, db, group_admin_token):
    """GROUP_ADMIN can access the contact list."""
    make_member(db)
    resp = client.get("/api/members/contacts",
                      headers=auth_header(group_admin_token))
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_group_admin_can_bulk_status(client, db, group_admin_token):
    """GROUP_ADMIN can perform bulk status updates."""
    m1 = make_member(db, email="a@example.com")
    m2 = make_member(db, email="b@example.com")
    resp = client.patch(
        "/api/members/bulk-status",
        headers=auth_header(group_admin_token),
        json={"member_ids": [m1.id, m2.id], "status": "PROCESSED"},
    )
    assert resp.status_code == 200


def test_group_admin_can_delete_member(client, db, group_admin_token):
    """GROUP_ADMIN can delete members."""
    member = make_member(db)
    resp = client.delete(f"/api/members/{member.id}",
                         headers=auth_header(group_admin_token))
    assert resp.status_code == 204


def test_group_admin_cannot_request_next_candidate(client, db, group_admin_token):
    """GROUP_ADMIN cannot use next-candidate (vetter-only)."""
    make_member(db)
    resp = client.post("/api/members/next-candidate",
                       headers=auth_header(group_admin_token))
    assert resp.status_code == 403


def test_group_admin_can_reclaim_stale(client, db, group_admin_token):
    """GROUP_ADMIN can trigger stale reclamation."""
    resp = client.post("/api/members/reclaim-stale",
                       headers=auth_header(group_admin_token))
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# User management — GROUP_ADMIN can create/edit/delete vetters only
# ---------------------------------------------------------------------------

def test_group_admin_can_list_users(client, group_admin_token, group_admin):
    """GROUP_ADMIN can list all users."""
    resp = client.get("/api/users", headers=auth_header(group_admin_token))
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_group_admin_can_create_vetter(client, group_admin_token):
    """GROUP_ADMIN can create a vetter account."""
    resp = client.post("/api/users", headers=auth_header(group_admin_token), json={
        "username": "newvetter",
        "password": "password123",
        "role": "VETTER",
        "full_name": "New Vetter",
    })
    assert resp.status_code == 201
    assert resp.json()["role"] == "VETTER"


def test_group_admin_cannot_create_super_admin(client, group_admin_token):
    """GROUP_ADMIN cannot create a SUPER_ADMIN."""
    resp = client.post("/api/users", headers=auth_header(group_admin_token), json={
        "username": "hackeradmin",
        "password": "password123",
        "role": "SUPER_ADMIN",
        "full_name": "Hacker Admin",
    })
    assert resp.status_code == 403
    assert "vetter" in resp.json()["detail"].lower()


def test_group_admin_cannot_create_group_admin(client, group_admin_token):
    """GROUP_ADMIN cannot create another GROUP_ADMIN."""
    resp = client.post("/api/users", headers=auth_header(group_admin_token), json={
        "username": "another-ga",
        "password": "password123",
        "role": "GROUP_ADMIN",
        "full_name": "Another GA",
    })
    assert resp.status_code == 403


def test_group_admin_can_update_vetter(client, db, group_admin_token):
    """GROUP_ADMIN can update a vetter's name/password."""
    vetter = User(
        username="editme",
        hashed_password=hash_password("password"),
        role=UserRole.VETTER,
        full_name="Edit Me",
        is_active=True,
    )
    db.add(vetter)
    db.commit()
    db.refresh(vetter)

    resp = client.patch(
        f"/api/users/{vetter.id}",
        headers=auth_header(group_admin_token),
        json={"full_name": "Edited Name"},
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Edited Name"


def test_group_admin_cannot_update_super_admin(client, db, group_admin_token):
    """GROUP_ADMIN cannot edit a SUPER_ADMIN user."""
    admin = User(
        username="realadmin",
        hashed_password=hash_password("password"),
        role=UserRole.SUPER_ADMIN,
        full_name="Real Admin",
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    resp = client.patch(
        f"/api/users/{admin.id}",
        headers=auth_header(group_admin_token),
        json={"full_name": "Hacked Name"},
    )
    assert resp.status_code == 403


def test_group_admin_cannot_promote_vetter_to_admin(client, db, group_admin_token):
    """GROUP_ADMIN cannot change a vetter's role to SUPER_ADMIN."""
    vetter = User(
        username="promoteme",
        hashed_password=hash_password("password"),
        role=UserRole.VETTER,
        full_name="Promote Me",
        is_active=True,
    )
    db.add(vetter)
    db.commit()
    db.refresh(vetter)

    resp = client.patch(
        f"/api/users/{vetter.id}",
        headers=auth_header(group_admin_token),
        json={"role": "SUPER_ADMIN"},
    )
    assert resp.status_code == 403


def test_group_admin_can_deactivate_vetter(client, db, group_admin_token):
    """GROUP_ADMIN can deactivate a vetter."""
    vetter = User(
        username="deactivateme",
        hashed_password=hash_password("password"),
        role=UserRole.VETTER,
        full_name="Deactivate Me",
        is_active=True,
    )
    db.add(vetter)
    db.commit()
    db.refresh(vetter)

    resp = client.patch(
        f"/api/users/{vetter.id}",
        headers=auth_header(group_admin_token),
        json={"is_active": False},
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


def test_group_admin_can_delete_vetter(client, db, group_admin_token):
    """GROUP_ADMIN can delete a vetter."""
    vetter = User(
        username="deleteme",
        hashed_password=hash_password("password"),
        role=UserRole.VETTER,
        full_name="Delete Me",
        is_active=True,
    )
    db.add(vetter)
    db.commit()
    db.refresh(vetter)

    resp = client.delete(
        f"/api/users/{vetter.id}",
        headers=auth_header(group_admin_token),
    )
    assert resp.status_code == 204


def test_group_admin_cannot_delete_super_admin(client, db, group_admin_token):
    """GROUP_ADMIN cannot delete a SUPER_ADMIN user."""
    admin = User(
        username="nodelete",
        hashed_password=hash_password("password"),
        role=UserRole.SUPER_ADMIN,
        full_name="No Delete",
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    resp = client.delete(
        f"/api/users/{admin.id}",
        headers=auth_header(group_admin_token),
    )
    assert resp.status_code == 403


def test_group_admin_cannot_delete_self(client, group_admin, group_admin_token):
    """GROUP_ADMIN cannot delete their own account."""
    resp = client.delete(
        f"/api/users/{group_admin.id}",
        headers=auth_header(group_admin_token),
    )
    assert resp.status_code == 400


def test_group_admin_cannot_delete_another_group_admin(client, db, group_admin_token):
    """GROUP_ADMIN cannot delete another GROUP_ADMIN."""
    other_ga = User(
        username="otherga",
        hashed_password=hash_password("password"),
        role=UserRole.GROUP_ADMIN,
        full_name="Other GA",
        is_active=True,
    )
    db.add(other_ga)
    db.commit()
    db.refresh(other_ga)

    resp = client.delete(
        f"/api/users/{other_ga.id}",
        headers=auth_header(group_admin_token),
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Edit user — role changes, password, active status
# ---------------------------------------------------------------------------

def test_super_admin_can_change_user_to_group_admin(client, db, admin_user, admin_token):
    """SUPER_ADMIN can promote a vetter to GROUP_ADMIN."""
    vetter = User(
        username="promote-to-ga",
        hashed_password=hash_password("password"),
        role=UserRole.VETTER,
        full_name="Soon GA",
        is_active=True,
    )
    db.add(vetter)
    db.commit()
    db.refresh(vetter)

    resp = client.patch(
        f"/api/users/{vetter.id}",
        headers=auth_header(admin_token),
        json={"role": "GROUP_ADMIN"},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "GROUP_ADMIN"


def test_super_admin_can_demote_group_admin_to_vetter(client, db, admin_user, admin_token):
    """SUPER_ADMIN can demote a GROUP_ADMIN to VETTER."""
    ga = User(
        username="demote-ga",
        hashed_password=hash_password("password"),
        role=UserRole.GROUP_ADMIN,
        full_name="Demote Me",
        is_active=True,
    )
    db.add(ga)
    db.commit()
    db.refresh(ga)

    resp = client.patch(
        f"/api/users/{ga.id}",
        headers=auth_header(admin_token),
        json={"role": "VETTER"},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "VETTER"


def test_group_admin_cannot_promote_vetter_to_group_admin(client, db, group_admin_token):
    """GROUP_ADMIN cannot promote a vetter to GROUP_ADMIN."""
    vetter = User(
        username="no-promote-ga",
        hashed_password=hash_password("password"),
        role=UserRole.VETTER,
        full_name="No Promote",
        is_active=True,
    )
    db.add(vetter)
    db.commit()
    db.refresh(vetter)

    resp = client.patch(
        f"/api/users/{vetter.id}",
        headers=auth_header(group_admin_token),
        json={"role": "GROUP_ADMIN"},
    )
    assert resp.status_code == 403


def test_group_admin_cannot_edit_another_group_admin(client, db, group_admin_token):
    """GROUP_ADMIN cannot edit another GROUP_ADMIN user."""
    other_ga = User(
        username="other-ga-edit",
        hashed_password=hash_password("password"),
        role=UserRole.GROUP_ADMIN,
        full_name="Other GA",
        is_active=True,
    )
    db.add(other_ga)
    db.commit()
    db.refresh(other_ga)

    resp = client.patch(
        f"/api/users/{other_ga.id}",
        headers=auth_header(group_admin_token),
        json={"full_name": "Hacked"},
    )
    assert resp.status_code == 403


def test_group_admin_can_change_vetter_password(client, db, group_admin_token):
    """GROUP_ADMIN can reset a vetter's password."""
    vetter = User(
        username="reset-pw",
        hashed_password=hash_password("old-password"),
        role=UserRole.VETTER,
        full_name="Reset PW",
        is_active=True,
    )
    db.add(vetter)
    db.commit()
    db.refresh(vetter)

    resp = client.patch(
        f"/api/users/{vetter.id}",
        headers=auth_header(group_admin_token),
        json={"password": "new-password-123"},
    )
    assert resp.status_code == 200

    # Verify new password works
    resp = client.post("/api/auth/login", json={
        "username": "reset-pw",
        "password": "new-password-123",
    })
    assert resp.status_code == 200


def test_group_admin_can_reactivate_vetter(client, db, group_admin_token):
    """GROUP_ADMIN can reactivate an inactive vetter."""
    vetter = User(
        username="reactivate-me",
        hashed_password=hash_password("password"),
        role=UserRole.VETTER,
        full_name="Reactivate Me",
        is_active=False,
    )
    db.add(vetter)
    db.commit()
    db.refresh(vetter)

    resp = client.patch(
        f"/api/users/{vetter.id}",
        headers=auth_header(group_admin_token),
        json={"is_active": True},
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True


def test_super_admin_can_edit_group_admin(client, db, admin_user, admin_token):
    """SUPER_ADMIN can edit a GROUP_ADMIN user."""
    ga = User(
        username="edit-ga",
        hashed_password=hash_password("password"),
        role=UserRole.GROUP_ADMIN,
        full_name="Edit GA",
        is_active=True,
    )
    db.add(ga)
    db.commit()
    db.refresh(ga)

    resp = client.patch(
        f"/api/users/{ga.id}",
        headers=auth_header(admin_token),
        json={"full_name": "Edited GA", "is_active": False},
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Edited GA"
    assert resp.json()["is_active"] is False


def test_super_admin_can_create_group_admin(client, admin_user, admin_token):
    """SUPER_ADMIN can create a GROUP_ADMIN user."""
    resp = client.post("/api/users", headers=auth_header(admin_token), json={
        "username": "new-ga",
        "password": "password123",
        "role": "GROUP_ADMIN",
        "full_name": "New Group Admin",
    })
    assert resp.status_code == 201
    assert resp.json()["role"] == "GROUP_ADMIN"


# ---------------------------------------------------------------------------
# Vetter still cannot access user management
# ---------------------------------------------------------------------------

def test_vetter_still_cannot_manage_users(client, db):
    """Verify vetters are still locked out of user management."""
    vetter = User(
        username="plainvetter",
        hashed_password=hash_password("password"),
        role=UserRole.VETTER,
        full_name="Plain Vetter",
        is_active=True,
    )
    db.add(vetter)
    db.commit()
    db.refresh(vetter)

    token = login(client, "plainvetter", "password")

    resp = client.get("/api/users", headers=auth_header(token))
    assert resp.status_code == 403

    resp = client.post("/api/users", headers=auth_header(token), json={
        "username": "bad", "password": "bad", "role": "VETTER", "full_name": "Bad",
    })
    assert resp.status_code == 403
