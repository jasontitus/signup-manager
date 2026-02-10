"""
CRITICAL SECURITY TESTS — Vetter isolation.

Ensures that vetters can only access members assigned to them.
These tests verify the core access control guarantee.
"""

from tests.conftest import make_member, auth_header
from app.models.member import MemberStatus


def test_vetter_cannot_access_other_vetter_member(
    client, db, vetter_user, vetter_user2, vetter_token
):
    """CRITICAL: Vetter A cannot access vetter B's member."""
    m = make_member(
        db, email="other@test.com",
        status=MemberStatus.ASSIGNED,
        assigned_vetter_id=vetter_user2.id,
    )
    resp = client.get(f"/api/members/{m.id}", headers=auth_header(vetter_token))
    assert resp.status_code == 403
    assert "permission" in resp.json()["detail"].lower()


def test_vetter_list_only_shows_assigned_members(
    client, db, vetter_user, vetter_user2, vetter_token
):
    """CRITICAL: List endpoint only returns the vetter's own assigned members."""
    make_member(
        db, first_name="Mine", email="mine@test.com",
        status=MemberStatus.ASSIGNED,
        assigned_vetter_id=vetter_user.id,
    )
    make_member(
        db, first_name="NotMine", email="notmine@test.com",
        status=MemberStatus.ASSIGNED,
        assigned_vetter_id=vetter_user2.id,
    )

    resp = client.get("/api/members", headers=auth_header(vetter_token))
    assert resp.status_code == 200
    members = resp.json()
    assert len(members) == 1
    assert members[0]["first_name"] == "Mine"


def test_vetter_can_access_assigned_member(
    client, db, vetter_user, vetter_token
):
    """Vetter can access their own assigned member and see decrypted PII."""
    m = make_member(
        db, first_name="John", email="john@test.com",
        status=MemberStatus.ASSIGNED,
        assigned_vetter_id=vetter_user.id,
    )
    resp = client.get(f"/api/members/{m.id}", headers=auth_header(vetter_token))
    assert resp.status_code == 200
    assert resp.json()["first_name"] == "John"


def test_vetter_cannot_update_other_vetter_member(
    client, db, vetter_user2, vetter_token
):
    """CRITICAL: Vetter cannot change status of another vetter's member."""
    m = make_member(
        db, email="noupdate@test.com",
        status=MemberStatus.ASSIGNED,
        assigned_vetter_id=vetter_user2.id,
    )
    resp = client.patch(
        f"/api/members/{m.id}/status",
        headers=auth_header(vetter_token),
        json={"status": "VETTED"},
    )
    assert resp.status_code == 403


def test_vetter_cannot_add_notes_to_other_vetter_member(
    client, db, vetter_user2, vetter_token
):
    """CRITICAL: Vetter cannot add notes to another vetter's member."""
    m = make_member(
        db, email="nonote@test.com",
        status=MemberStatus.ASSIGNED,
        assigned_vetter_id=vetter_user2.id,
    )
    resp = client.post(
        f"/api/members/{m.id}/notes",
        headers=auth_header(vetter_token),
        json={"note": "Sneaky note"},
    )
    assert resp.status_code == 403
