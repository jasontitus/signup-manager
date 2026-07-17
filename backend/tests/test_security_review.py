"""Regression tests for the 2026-07 security/reliability review.

Each test pins a specific fix:
- /members/queue-count route no longer shadowed by /members/{member_id}
- /tags/categories/{key}/usage no longer 500s (hybrid property in query)
- MEMBER_DELETED audit entry survives member deletion
- CSV export neutralizes spreadsheet formula injection
- CSV export validates sort parameters
- Login brute-force throttling (failed attempts only; success resets)
- JWT with a non-numeric subject is rejected with 401, not 500
- Public application input length limits
- Startup refuses to run without security-critical secrets
- Vault distinguishes wrong password from corrupt vault
- Search survives an undecryptable member row
"""

import base64
import json
import os

import pytest
from jose import jwt

from app.config import settings
from app.main import validate_secrets
from app.models.audit_log import AuditLog
from app.models.member import Member
from app.routers.members import escape_csv_formula
from app.services.rate_limit import FailedAttemptLimiter
from app.vault import VaultManager

from tests.conftest import auth_header, make_member


# ---------------------------------------------------------------------------
# Route ordering: /members/queue-count
# ---------------------------------------------------------------------------

class TestQueueCountRoute:
    def test_queue_count_returns_200_for_admin(self, client, admin_token, pending_member):
        resp = client.get("/api/members/queue-count", headers=auth_header(admin_token))
        assert resp.status_code == 200
        assert resp.json() == {"pending_count": 1}

    def test_queue_count_returns_200_for_vetter(self, client, vetter_token):
        resp = client.get("/api/members/queue-count", headers=auth_header(vetter_token))
        assert resp.status_code == 200
        assert "pending_count" in resp.json()


# ---------------------------------------------------------------------------
# Tag usage endpoint (hybrid property crash)
# ---------------------------------------------------------------------------

class TestTagUsageEndpoint:
    def test_usage_counts_members_with_tags(self, client, db, admin_token):
        # Use a real category from the checked-in tag config
        config_resp = client.get("/api/tags", headers=auth_header(admin_token))
        assert config_resp.status_code == 200
        category = config_resp.json()["categories"][0]
        key, option = category["key"], category["options"][0]

        member = make_member(db, email="tagged@example.com")
        member.tags = {key: option}
        db.commit()
        make_member(db, email="untagged@example.com")

        resp = client.get(f"/api/tags/categories/{key}/usage", headers=auth_header(admin_token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["usage"][option] == 1
        assert body["total_members_using"] == 1

    def test_usage_unknown_category_404(self, client, admin_token):
        resp = client.get("/api/tags/categories/nope/usage", headers=auth_header(admin_token))
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Audit trail survives member deletion
# ---------------------------------------------------------------------------

class TestDeleteAuditTrail:
    def test_member_deleted_entry_survives(self, client, db, admin_token, pending_member):
        member_id = pending_member.id
        resp = client.delete(f"/api/members/{member_id}", headers=auth_header(admin_token))
        assert resp.status_code == 204

        assert db.query(Member).filter(Member.id == member_id).first() is None
        deletion_logs = db.query(AuditLog).filter(AuditLog.action == "MEMBER_DELETED").all()
        assert len(deletion_logs) == 1
        assert f"(ID: {member_id})" in deletion_logs[0].details
        # The member's own audit history is purged
        assert db.query(AuditLog).filter(AuditLog.member_id == member_id).count() == 0


# ---------------------------------------------------------------------------
# CSV export: formula injection + sort validation
# ---------------------------------------------------------------------------

class TestCsvExport:
    @pytest.mark.parametrize("payload,expected", [
        ("=HYPERLINK(\"http://evil\")", "'=HYPERLINK(\"http://evil\")"),
        ("+1-555", "'+1-555"),
        ("-cmd", "'-cmd"),
        ("@import", "'@import"),
        ("\tx", "'\tx"),
        ("normal", "normal"),
        ("", ""),
    ])
    def test_escape_csv_formula(self, payload, expected):
        assert escape_csv_formula(payload) == expected

    def test_export_escapes_formula_cells(self, client, db, admin_token):
        make_member(db, first_name="=2+5", last_name="Doe", email="csv@example.com")
        resp = client.get(
            "/api/members/export?fields=first_name,last_name",
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 200
        assert "'=2+5" in resp.text

    def test_export_rejects_invalid_sort_field(self, client, admin_token, pending_member):
        resp = client.get(
            "/api/members/export?fields=first_name&sort_by=hashed_password",
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 400

    def test_export_rejects_invalid_sort_order(self, client, admin_token, pending_member):
        resp = client.get(
            "/api/members/export?fields=first_name&sort_order=sideways",
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Login brute-force throttling
# ---------------------------------------------------------------------------

class TestLoginThrottling:
    def test_blocked_after_repeated_failures(self, client, admin_user):
        for _ in range(5):
            resp = client.post("/api/auth/login", json={
                "username": "admin", "password": "wrong",
            })
            assert resp.status_code == 401
        resp = client.post("/api/auth/login", json={
            "username": "admin", "password": "wrong",
        })
        assert resp.status_code == 429
        # Even the correct password is blocked while throttled
        resp = client.post("/api/auth/login", json={
            "username": "admin", "password": "admin-password",
        })
        assert resp.status_code == 429

    def test_success_resets_counter(self, client, admin_user):
        for _ in range(3):
            client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
        resp = client.post("/api/auth/login", json={
            "username": "admin", "password": "admin-password",
        })
        assert resp.status_code == 200
        # Counter cleared: three more failures don't hit the limit
        for _ in range(3):
            resp = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
        assert resp.status_code == 401

    def test_throttle_is_per_username(self, client, admin_user, vetter_user):
        for _ in range(6):
            client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
        # A different account from the same client is unaffected
        resp = client.post("/api/auth/login", json={
            "username": "vetter1", "password": "vetter-password",
        })
        assert resp.status_code == 200


class TestFailedAttemptLimiter:
    def test_window_expiry(self, monkeypatch):
        limiter = FailedAttemptLimiter(max_failures=2, window_seconds=100)
        now = [1000.0]
        monkeypatch.setattr("app.services.rate_limit.time.monotonic", lambda: now[0])

        limiter.record_failure("k")
        limiter.record_failure("k")
        assert limiter.is_blocked("k")
        now[0] += 101  # window passes
        assert not limiter.is_blocked("k")


# ---------------------------------------------------------------------------
# Auth hardening
# ---------------------------------------------------------------------------

class TestAuthHardening:
    def test_non_numeric_token_subject_is_401(self, client):
        token = jwt.encode({"sub": "not-a-number"}, settings.SECRET_KEY, algorithm="HS256")
        resp = client.get("/api/members", headers=auth_header(token))
        assert resp.status_code == 401

    def test_missing_subject_is_401(self, client):
        token = jwt.encode({"foo": "bar"}, settings.SECRET_KEY, algorithm="HS256")
        resp = client.get("/api/members", headers=auth_header(token))
        assert resp.status_code == 401

    def test_oversized_login_payload_rejected(self, client, admin_user):
        resp = client.post("/api/auth/login", json={
            "username": "admin", "password": "x" * 100_000,
        })
        assert resp.status_code == 422

    def test_validate_secrets_raises_when_missing(self):
        original = settings.SECRET_KEY
        try:
            object.__setattr__(settings, "SECRET_KEY", "")
            with pytest.raises(RuntimeError, match="SECRET_KEY"):
                validate_secrets()
        finally:
            object.__setattr__(settings, "SECRET_KEY", original)

    def test_validate_secrets_passes_when_configured(self):
        validate_secrets()  # conftest configures all three secrets


# ---------------------------------------------------------------------------
# Public application input limits
# ---------------------------------------------------------------------------

def _application(**overrides):
    base = {
        "first_name": "Alice",
        "last_name": "Applicant",
        "street_address": "1 Main St",
        "city": "Springfield",
        "zip_code": "62701",
        "phone_number": "555-0001",
        "email": "alice.applicant@example.com",
    }
    base.update(overrides)
    return base


class TestPublicApplicationLimits:
    def test_valid_application_accepted(self, client):
        resp = client.post("/api/public/apply", json=_application())
        assert resp.status_code == 201

    def test_oversized_standard_field_rejected(self, client):
        resp = client.post("/api/public/apply", json=_application(first_name="x" * 5000))
        assert resp.status_code == 400

    def test_oversized_custom_field_rejected(self, client):
        # signal_channels has no maxLength in the form config; the
        # global fallback cap must still bound it.
        resp = client.post(
            "/api/public/apply",
            json=_application(signal_channels="x" * 6000),
        )
        assert resp.status_code == 400

    def test_duplicate_email_conflict(self, client):
        assert client.post("/api/public/apply", json=_application()).status_code == 201
        resp = client.post("/api/public/apply", json=_application())
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Vault error handling
# ---------------------------------------------------------------------------

def _write_vault(path, password, payload_bytes):
    """Create a vault file the way vault.py does."""
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    salt = os.urandom(16)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=1000)
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    data = Fernet(key).encrypt(payload_bytes).decode()
    with open(path, "w") as f:
        json.dump({
            "salt": base64.b64encode(salt).decode(),
            "iterations": 1000,
            "data": data,
        }, f)


class TestVaultErrorHandling:
    @pytest.fixture
    def vault_path(self, tmp_path, monkeypatch):
        path = str(tmp_path / ".vault")
        monkeypatch.setattr(settings, "VAULT_FILE", path)
        return path

    def test_wrong_password_returns_false(self, vault_path):
        _write_vault(vault_path, "correct-horse", json.dumps({"SECRET_KEY": "s"}).encode())
        manager = VaultManager()
        assert manager.unlock("wrong-password") is False
        assert not manager.is_unlocked

    def test_correct_password_unlocks(self, vault_path):
        _write_vault(vault_path, "correct-horse", json.dumps({"SECRET_KEY": "s"}).encode())
        manager = VaultManager()
        assert manager.unlock("correct-horse") is True
        assert manager.secrets == {"SECRET_KEY": "s"}

    def test_corrupt_payload_raises_instead_of_wrong_password(self, vault_path):
        _write_vault(vault_path, "correct-horse", b"this is not json")
        manager = VaultManager()
        with pytest.raises(RuntimeError, match="corrupt"):
            manager.unlock("correct-horse")

    def test_missing_vault_raises_file_not_found(self, vault_path):
        manager = VaultManager()
        with pytest.raises(FileNotFoundError):
            manager.unlock("anything")


# ---------------------------------------------------------------------------
# Search resilience
# ---------------------------------------------------------------------------

class TestSearchResilience:
    def test_search_skips_undecryptable_member(self, client, db, admin_token):
        good = make_member(db, first_name="Findme", email="good@example.com")
        bad = make_member(db, first_name="Findme", email="bad@example.com")
        # Corrupt one member's ciphertext directly in the DB
        bad._first_name = "not-valid-ciphertext"
        db.commit()

        resp = client.get("/api/members/search/query?q=findme", headers=auth_header(admin_token))
        assert resp.status_code == 200
        ids = [m["id"] for m in resp.json()]
        assert good.id in ids
        assert bad.id not in ids
