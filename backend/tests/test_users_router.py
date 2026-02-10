"""Tests for the users router — CRUD and RBAC."""

from tests.conftest import auth_header


# ── List users ─────────────────────────────────────────────────────────────

def test_list_users_as_admin(client, admin_token, admin_user):
    """Admin can list all users."""
    resp = client.get("/api/users", headers=auth_header(admin_token))
    assert resp.status_code == 200
    users = resp.json()
    assert len(users) >= 1
    assert any(u["username"] == "admin" for u in users)


def test_list_users_as_vetter_forbidden(client, vetter_token):
    """Vetters cannot list users."""
    resp = client.get("/api/users", headers=auth_header(vetter_token))
    assert resp.status_code == 403


def test_list_users_unauthenticated(client):
    """Unauthenticated requests are rejected."""
    resp = client.get("/api/users")
    assert resp.status_code == 403


# ── Create user ────────────────────────────────────────────────────────────

def test_create_user(client, admin_token):
    """Admin can create a new user."""
    resp = client.post("/api/users", headers=auth_header(admin_token), json={
        "username": "newvetter",
        "password": "password123",
        "role": "VETTER",
        "full_name": "New Vetter",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "newvetter"
    assert data["role"] == "VETTER"
    assert data["is_active"] is True


def test_create_duplicate_username(client, admin_token, admin_user):
    """Duplicate username returns 409."""
    resp = client.post("/api/users", headers=auth_header(admin_token), json={
        "username": "admin",
        "password": "password123",
        "role": "VETTER",
        "full_name": "Duplicate",
    })
    assert resp.status_code == 409


def test_create_user_as_vetter_forbidden(client, vetter_token):
    """Vetters cannot create users."""
    resp = client.post("/api/users", headers=auth_header(vetter_token), json={
        "username": "hacker",
        "password": "password123",
        "role": "SUPER_ADMIN",
        "full_name": "Hacker",
    })
    assert resp.status_code == 403


# ── Get user ───────────────────────────────────────────────────────────────

def test_get_user(client, admin_token, admin_user):
    """Admin can get a specific user."""
    resp = client.get(f"/api/users/{admin_user.id}", headers=auth_header(admin_token))
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin"


def test_get_user_not_found(client, admin_token):
    """Nonexistent user ID returns 404."""
    resp = client.get("/api/users/9999", headers=auth_header(admin_token))
    assert resp.status_code == 404


# ── Update user ────────────────────────────────────────────────────────────

def test_update_user_role(client, admin_token, vetter_user):
    """Admin can change a user's role."""
    resp = client.patch(
        f"/api/users/{vetter_user.id}",
        headers=auth_header(admin_token),
        json={"role": "SUPER_ADMIN"},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "SUPER_ADMIN"


def test_update_user_deactivate(client, admin_token, vetter_user):
    """Admin can deactivate a user."""
    resp = client.patch(
        f"/api/users/{vetter_user.id}",
        headers=auth_header(admin_token),
        json={"is_active": False},
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


def test_update_user_password(client, admin_token, vetter_user):
    """Admin can change a user's password."""
    resp = client.patch(
        f"/api/users/{vetter_user.id}",
        headers=auth_header(admin_token),
        json={"password": "new-password-123"},
    )
    assert resp.status_code == 200

    # Verify the new password works
    resp = client.post("/api/auth/login", json={
        "username": "vetter1",
        "password": "new-password-123",
    })
    assert resp.status_code == 200


def test_update_nonexistent_user(client, admin_token):
    """Updating a nonexistent user returns 404."""
    resp = client.patch(
        "/api/users/9999",
        headers=auth_header(admin_token),
        json={"full_name": "Ghost"},
    )
    assert resp.status_code == 404


# ── Delete user ────────────────────────────────────────────────────────────

def test_delete_user(client, admin_token, vetter_user):
    """Admin can delete another user."""
    resp = client.delete(
        f"/api/users/{vetter_user.id}",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 204

    # Verify user is gone
    resp = client.get(
        f"/api/users/{vetter_user.id}",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 404


def test_delete_self_forbidden(client, admin_token, admin_user):
    """Admin cannot delete their own account."""
    resp = client.delete(
        f"/api/users/{admin_user.id}",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 400
    assert "own account" in resp.json()["detail"].lower()


def test_delete_nonexistent_user(client, admin_token):
    """Deleting a nonexistent user returns 404."""
    resp = client.delete("/api/users/9999", headers=auth_header(admin_token))
    assert resp.status_code == 404
