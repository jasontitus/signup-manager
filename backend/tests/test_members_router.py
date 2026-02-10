"""Tests for the members router — CRUD, search, RBAC, and vetter isolation."""

from tests.conftest import make_member, auth_header
from app.models.member import MemberStatus
from app.models.audit_log import AuditLog


# ── List members ───────────────────────────────────────────────────────────

def test_list_members_as_admin(client, db, admin_token):
    """Admin sees all members."""
    make_member(db, email="a@test.com")
    make_member(db, first_name="Jane", email="b@test.com")

    resp = client.get("/api/members", headers=auth_header(admin_token))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_list_members_as_vetter_only_assigned(client, db, vetter_user, vetter_token):
    """Vetter only sees members assigned to them."""
    make_member(db, email="unassigned@test.com")
    make_member(
        db, email="assigned@test.com",
        status=MemberStatus.ASSIGNED,
        assigned_vetter_id=vetter_user.id,
    )

    resp = client.get("/api/members", headers=auth_header(vetter_token))
    assert resp.status_code == 200
    members = resp.json()
    assert len(members) == 1
    assert members[0]["status"] == "ASSIGNED"


def test_list_members_filter_by_status(client, db, admin_token, vetter_user):
    """Status filter works."""
    make_member(db, email="pending@test.com", status=MemberStatus.PENDING)
    make_member(
        db, email="assigned@test.com",
        status=MemberStatus.ASSIGNED,
        assigned_vetter_id=vetter_user.id,
    )

    resp = client.get(
        "/api/members?status_filter=PENDING",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 200
    assert all(m["status"] == "PENDING" for m in resp.json())


def test_list_members_unauthenticated(client):
    """Unauthenticated request is rejected."""
    resp = client.get("/api/members")
    assert resp.status_code == 403


# ── Get member detail ──────────────────────────────────────────────────────

def test_get_member_detail_as_admin(client, db, admin_token):
    """Admin can view any member's decrypted PII."""
    m = make_member(db, first_name="Alice", email="alice@test.com")

    resp = client.get(f"/api/members/{m.id}", headers=auth_header(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["first_name"] == "Alice"
    assert data["email"] == "alice@test.com"
    assert data["street_address"] == "123 Test St"


def test_get_member_logs_audit(client, db, admin_token, admin_user):
    """Viewing PII creates an audit log entry."""
    m = make_member(db, email="audit@test.com")
    client.get(f"/api/members/{m.id}", headers=auth_header(admin_token))

    logs = db.query(AuditLog).filter(
        AuditLog.action == "VIEWED_PII",
        AuditLog.member_id == m.id,
    ).all()
    assert len(logs) == 1
    assert logs[0].user_id == admin_user.id


def test_get_member_not_found(client, admin_token):
    """Nonexistent member returns 404."""
    resp = client.get("/api/members/9999", headers=auth_header(admin_token))
    assert resp.status_code == 404


def test_vetter_cannot_view_other_vetters_member(
    client, db, vetter_user, vetter_user2, vetter_token
):
    """Vetter cannot access a member assigned to another vetter."""
    m = make_member(
        db, email="other@test.com",
        status=MemberStatus.ASSIGNED,
        assigned_vetter_id=vetter_user2.id,
    )
    resp = client.get(f"/api/members/{m.id}", headers=auth_header(vetter_token))
    assert resp.status_code == 403


# ── Update member status ──────────────────────────────────────────────────

def test_update_status(client, db, admin_token, vetter_user):
    """Admin can change member status."""
    m = make_member(
        db, email="status@test.com",
        status=MemberStatus.ASSIGNED,
        assigned_vetter_id=vetter_user.id,
    )
    resp = client.patch(
        f"/api/members/{m.id}/status",
        headers=auth_header(admin_token),
        json={"status": "VETTED"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "VETTED"


def test_vetter_can_update_own_member_status(client, db, vetter_user, vetter_token):
    """Vetter can change status of their assigned member."""
    m = make_member(
        db, email="vetterstat@test.com",
        status=MemberStatus.ASSIGNED,
        assigned_vetter_id=vetter_user.id,
    )
    resp = client.patch(
        f"/api/members/{m.id}/status",
        headers=auth_header(vetter_token),
        json={"status": "VETTED"},
    )
    assert resp.status_code == 200


def test_vetter_cannot_update_other_member_status(
    client, db, vetter_user2, vetter_token
):
    """Vetter cannot change status of another vetter's member."""
    m = make_member(
        db, email="otherupd@test.com",
        status=MemberStatus.ASSIGNED,
        assigned_vetter_id=vetter_user2.id,
    )
    resp = client.patch(
        f"/api/members/{m.id}/status",
        headers=auth_header(vetter_token),
        json={"status": "REJECTED"},
    )
    assert resp.status_code == 403


# ── Add notes ──────────────────────────────────────────────────────────────

def test_add_note(client, db, admin_token):
    """Admin can add notes to a member."""
    m = make_member(db, email="note@test.com")
    resp = client.post(
        f"/api/members/{m.id}/notes",
        headers=auth_header(admin_token),
        json={"note": "Looks good"},
    )
    assert resp.status_code == 200
    assert "Looks good" in resp.json()["notes"]


def test_append_multiple_notes(client, db, admin_token):
    """Multiple notes are appended, not overwritten."""
    m = make_member(db, email="multi-note@test.com")

    client.post(
        f"/api/members/{m.id}/notes",
        headers=auth_header(admin_token),
        json={"note": "First note"},
    )
    resp = client.post(
        f"/api/members/{m.id}/notes",
        headers=auth_header(admin_token),
        json={"note": "Second note"},
    )
    notes = resp.json()["notes"]
    assert "First note" in notes
    assert "Second note" in notes


# ── Search ─────────────────────────────────────────────────────────────────

def test_search_by_first_name(client, db, admin_token):
    """Search finds members by decrypted first name."""
    make_member(db, first_name="Zebediah", email="zeb@test.com")

    resp = client.get(
        "/api/members/search/query?q=Zebediah",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["first_name"] == "Zebediah"


def test_search_by_city(client, db, admin_token):
    """Search finds members by decrypted city."""
    make_member(db, city="Gotham", email="gotham@test.com")

    resp = client.get(
        "/api/members/search/query?q=Gotham",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_search_by_notes(client, db, admin_token):
    """Search finds members by notes (SQL query, not encrypted)."""
    m = make_member(db, email="notesearch@test.com")
    client.post(
        f"/api/members/{m.id}/notes",
        headers=auth_header(admin_token),
        json={"note": "UniqueMarker12345"},
    )

    resp = client.get(
        "/api/members/search/query?q=UniqueMarker12345",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_search_no_results(client, db, admin_token):
    """Search with no matches returns empty list."""
    make_member(db, email="noresult@test.com")

    resp = client.get(
        "/api/members/search/query?q=ZZZZZZNOTFOUND",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 0


def test_search_respects_vetter_isolation(client, db, vetter_user, vetter_user2, vetter_token):
    """Vetter search only returns their own assigned members."""
    make_member(
        db, first_name="Searchable", email="v1@test.com",
        status=MemberStatus.ASSIGNED,
        assigned_vetter_id=vetter_user.id,
    )
    make_member(
        db, first_name="Searchable", email="v2@test.com",
        status=MemberStatus.ASSIGNED,
        assigned_vetter_id=vetter_user2.id,
    )

    resp = client.get(
        "/api/members/search/query?q=Searchable",
        headers=auth_header(vetter_token),
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1  # Only their own


# ── Next candidate ─────────────────────────────────────────────────────────

def test_next_candidate_assigns_pending(client, db, vetter_user, vetter_token):
    """Next-candidate endpoint assigns the oldest pending member."""
    m = make_member(db, email="next@test.com")

    resp = client.post("/api/members/next-candidate", headers=auth_header(vetter_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == m.id
    assert data["status"] == "ASSIGNED"


def test_next_candidate_returns_null_when_none(client, vetter_token):
    """Next-candidate returns null when no pending members exist."""
    resp = client.post("/api/members/next-candidate", headers=auth_header(vetter_token))
    assert resp.status_code == 200
    assert resp.json() is None


def test_next_candidate_admin_forbidden(client, admin_token):
    """Only vetters can request next candidate."""
    resp = client.post("/api/members/next-candidate", headers=auth_header(admin_token))
    assert resp.status_code == 403


# ── Delete member ──────────────────────────────────────────────────────────

def test_delete_member(client, db, admin_token):
    """Admin can delete a member."""
    m = make_member(db, email="delete@test.com")

    resp = client.delete(f"/api/members/{m.id}", headers=auth_header(admin_token))
    assert resp.status_code == 204

    # Verify it's gone
    resp = client.get(f"/api/members/{m.id}", headers=auth_header(admin_token))
    assert resp.status_code == 404


def test_delete_member_as_vetter_forbidden(client, db, vetter_user, vetter_token):
    """Vetters cannot delete members."""
    m = make_member(
        db, email="nodelete@test.com",
        status=MemberStatus.ASSIGNED,
        assigned_vetter_id=vetter_user.id,
    )
    resp = client.delete(f"/api/members/{m.id}", headers=auth_header(vetter_token))
    assert resp.status_code == 403


def test_delete_nonexistent_member(client, admin_token):
    """Deleting nonexistent member returns 404."""
    resp = client.delete("/api/members/9999", headers=auth_header(admin_token))
    assert resp.status_code == 404
