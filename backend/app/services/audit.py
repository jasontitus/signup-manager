from datetime import datetime
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog


class AuditService:
    """Service for logging all PII access and sensitive actions."""

    @staticmethod
    def log_action(
        db: Session,
        user_id: int,
        member_id: int,
        action: str,
        details: str = None
    ) -> AuditLog:
        """Log an audit event."""
        audit_entry = AuditLog(
            user_id=user_id,
            member_id=member_id,
            action=action,
            details=details,
            timestamp=datetime.utcnow()
        )
        db.add(audit_entry)
        db.commit()
        db.refresh(audit_entry)
        return audit_entry


# Singleton instance
audit_service = AuditService()
