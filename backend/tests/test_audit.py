"""Tests for the audit logging service."""

from app.services.audit import audit_service
from app.models.audit_log import AuditLog


def test_log_action_creates_entry(db, admin_user, pending_member):
    """Audit log entry is created and persisted."""
    entry = audit_service.log_action(
        db=db,
        user_id=admin_user.id,
        member_id=pending_member.id,
        action="TEST_ACTION",
        details="Test details",
    )
    assert entry.id is not None
    assert entry.user_id == admin_user.id
    assert entry.member_id == pending_member.id
    assert entry.action == "TEST_ACTION"
    assert entry.details == "Test details"
    assert entry.timestamp is not None


def test_log_action_with_null_member_id(db, admin_user):
    """Audit log works with null member_id (system-wide actions)."""
    entry = audit_service.log_action(
        db=db,
        user_id=admin_user.id,
        member_id=None,
        action="SYSTEM_ACTION",
        details="No specific member",
    )
    assert entry.id is not None
    assert entry.member_id is None


def test_log_action_persists_to_database(db, admin_user, pending_member):
    """Audit entry is retrievable from the database."""
    audit_service.log_action(
        db=db,
        user_id=admin_user.id,
        member_id=pending_member.id,
        action="PERSIST_TEST",
    )
    logs = db.query(AuditLog).filter(AuditLog.action == "PERSIST_TEST").all()
    assert len(logs) == 1
    assert logs[0].user_id == admin_user.id


def test_multiple_log_entries(db, admin_user, pending_member):
    """Multiple audit entries can be created for the same member."""
    for i in range(3):
        audit_service.log_action(
            db=db,
            user_id=admin_user.id,
            member_id=pending_member.id,
            action=f"ACTION_{i}",
        )
    logs = db.query(AuditLog).filter(
        AuditLog.member_id == pending_member.id
    ).all()
    assert len(logs) == 3
