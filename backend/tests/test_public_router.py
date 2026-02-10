"""Tests for the public router — application submission and form config."""

from app.models.member import Member


# ── Form config ────────────────────────────────────────────────────────────

def test_get_form_config(client):
    """Public endpoint returns form configuration."""
    resp = client.get("/api/public/form-config")
    assert resp.status_code == 200
    data = resp.json()
    assert "fields" in data
    assert len(data["fields"]) > 0


# ── Submit application ─────────────────────────────────────────────────────

def test_submit_valid_application(client, db):
    """Valid application is accepted and stored encrypted."""
    resp = client.post("/api/public/apply", json={
        "first_name": "Alice",
        "last_name": "Wonderland",
        "street_address": "1 Rabbit Hole",
        "city": "Wonderland",
        "zip_code": "00001",
        "phone_number": "555-1234",
        "email": "alice@wonderland.com",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "application_id" in data
    assert data["message"] == "Application submitted successfully"

    # Verify data is encrypted in the database
    member = db.query(Member).filter(Member.id == data["application_id"]).first()
    assert member is not None
    # Raw column should be ciphertext (not the plaintext)
    assert member._first_name != "Alice"
    assert member._email != "alice@wonderland.com"
    # Hybrid properties should decrypt
    assert member.first_name == "Alice"
    assert member.email == "alice@wonderland.com"


def test_submit_with_custom_fields(client, db):
    """Application with custom fields stores them encrypted."""
    resp = client.post("/api/public/apply", json={
        "first_name": "Bob",
        "last_name": "Builder",
        "street_address": "42 Fix-It Lane",
        "city": "Tooltown",
        "zip_code": "12345",
        "phone_number": "555-5678",
        "email": "bob@builder.com",
        "occupational_background": "Construction",
        "know_member": "Yes, Wendy",
        "hoped_impact": "Build more things",
    })
    assert resp.status_code == 201

    member = db.query(Member).filter(Member.id == resp.json()["application_id"]).first()
    custom = member.custom_fields
    assert custom.get("occupational_background") == "Construction"


def test_submit_missing_required_field(client):
    """Missing required field returns 400."""
    resp = client.post("/api/public/apply", json={
        "first_name": "Incomplete",
        # missing last_name, street_address, etc.
    })
    assert resp.status_code == 400


def test_submit_duplicate_email(client, db):
    """Duplicate email (via blind index) returns 409."""
    payload = {
        "first_name": "Dup",
        "last_name": "Test",
        "street_address": "1 Main",
        "city": "Town",
        "zip_code": "11111",
        "phone_number": "555-0000",
        "email": "duplicate@test.com",
    }
    resp1 = client.post("/api/public/apply", json=payload)
    assert resp1.status_code == 201

    resp2 = client.post("/api/public/apply", json=payload)
    assert resp2.status_code == 409
    assert "already exists" in resp2.json()["detail"].lower()


def test_submit_duplicate_email_case_insensitive(client, db):
    """Duplicate detection is case-insensitive."""
    base = {
        "first_name": "Case",
        "last_name": "Test",
        "street_address": "1 Main",
        "city": "Town",
        "zip_code": "11111",
        "phone_number": "555-0000",
    }

    resp1 = client.post("/api/public/apply", json={**base, "email": "UPPER@test.com"})
    assert resp1.status_code == 201

    resp2 = client.post("/api/public/apply", json={**base, "email": "upper@test.com"})
    assert resp2.status_code == 409


def test_submit_creates_pending_status(client, db):
    """New applications start with PENDING status."""
    resp = client.post("/api/public/apply", json={
        "first_name": "Status",
        "last_name": "Check",
        "street_address": "1 Main",
        "city": "Town",
        "zip_code": "11111",
        "phone_number": "555-0000",
        "email": "status@check.com",
    })
    assert resp.status_code == 201

    member = db.query(Member).filter(Member.id == resp.json()["application_id"]).first()
    assert member.status.value == "PENDING"
    assert member.assigned_vetter_id is None
