"""Tests for the auth router — login, auto-assign, and stale reclamation."""

from datetime import datetime, timedelta
from tests.conftest import make_member, auth_header
from app.models.member import Member, MemberStatus


# ── Login ──────────────────────────────────────────────────────────────────

def test_login_success(client, admin_user):
    """Successful login returns a token and user info."""
    resp = client.post("/api/auth/login", json={
        "username": "admin",
        "password": "admin-password",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["username"] == "admin"
    assert data["role"] == "SUPER_ADMIN"
    assert data["full_name"] == "Test Admin"
    assert data["user_id"] == admin_user.id


def test_login_wrong_password(client, admin_user):
    """Wrong password returns 401."""
    resp = client.post("/api/auth/login", json={
        "username": "admin",
        "password": "wrong",
    })
    assert resp.status_code == 401


def test_login_nonexistent_user(client):
    """Nonexistent username returns 401."""
    resp = client.post("/api/auth/login", json={
        "username": "nobody",
        "password": "anything",
    })
    assert resp.status_code == 401


def test_login_inactive_user(client, inactive_user):
    """Inactive user returns 403."""
    resp = client.post("/api/auth/login", json={
        "username": "inactive",
        "password": "inactive-password",
    })
    assert resp.status_code == 403


# ── Auto-assign on vetter login ───────────────────────────────────────────

def test_vetter_login_auto_assigns_pending_member(client, db, vetter_user):
    """When a vetter logs in, the oldest pending member is auto-assigned."""
    m = make_member(db, email="pending@test.com")
    assert m.status == MemberStatus.PENDING

    client.post("/api/auth/login", json={
        "username": "vetter1",
        "password": "vetter-password",
    })

    db.refresh(m)
    assert m.status == MemberStatus.ASSIGNED
    assert m.assigned_vetter_id == vetter_user.id


def test_admin_login_does_not_auto_assign(client, db, admin_user):
    """Admin login should NOT trigger auto-assignment."""
    m = make_member(db, email="admin-test@test.com")

    client.post("/api/auth/login", json={
        "username": "admin",
        "password": "admin-password",
    })

    db.refresh(m)
    assert m.status == MemberStatus.PENDING


# ── Stale reclamation ─────────────────────────────────────────────────────

def test_stale_assignment_reclaimed_on_login(client, db, vetter_user, vetter_user2):
    """Assignments older than 7 days are reclaimed when a vetter logs in."""
    m = make_member(
        db,
        email="stale@test.com",
        status=MemberStatus.ASSIGNED,
        assigned_vetter_id=vetter_user.id,
    )
    # Backdate the updated_at to 8 days ago
    stale_date = datetime.utcnow() - timedelta(days=8)
    db.execute(
        Member.__table__.update()
        .where(Member.__table__.c.id == m.id)
        .values(updated_at=stale_date)
    )
    db.commit()

    # Login as vetter2 — should trigger stale reclamation + auto-assign
    client.post("/api/auth/login", json={
        "username": "vetter2",
        "password": "vetter-password",
    })

    db.refresh(m)
    # The stale member should now be assigned to vetter2
    assert m.assigned_vetter_id == vetter_user2.id
    assert m.status == MemberStatus.ASSIGNED


def test_manual_reclaim_stale_admin_only(client, admin_token, vetter_token):
    """Only admins can manually trigger stale reclamation."""
    # Admin should succeed
    resp = client.post("/api/members/reclaim-stale", headers=auth_header(admin_token))
    assert resp.status_code == 200

    # Vetter should be forbidden
    resp = client.post("/api/members/reclaim-stale", headers=auth_header(vetter_token))
    assert resp.status_code == 403
