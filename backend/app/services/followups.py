"""Scheduled follow-up pings.

One month after a member is marked VETTED, they are moved to
ONE_MONTH_FOLLOWUP and the follow-up contact is emailed. Six months after
a member enters IN_SIGNAL (the resting status), they are moved to
SIX_MONTH_FOLLOWUP and the follow-up contact is emailed. Returning a
member to IN_SIGNAL restarts the six-month timer, so members resurface
for a check-in on a recurring loop.
"""
import logging
from datetime import datetime, timedelta

from app.config import settings
from app.database import SessionLocal
from app.models.member import Member, MemberStatus
from app.services.audit import audit_service
from app.services.notifications import send_notification

logger = logging.getLogger(__name__)

ONE_MONTH = timedelta(days=30)
SIX_MONTHS = timedelta(days=182)


def run_followup_checks():
    """Run one pass of the follow-up checks. Called periodically."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()

        # --- One-month follow-up: 30 days after vetting ---
        # Members may already have moved to IN_SIGNAL by then; they still
        # get their one-month check-in.
        one_month_due = db.query(Member).filter(
            Member.status.in_([MemberStatus.VETTED, MemberStatus.IN_SIGNAL]),
            Member.vetted_at != None,
            Member.vetted_at <= now - ONE_MONTH,
            Member.one_month_followup_sent == False,
        ).all()

        for m in one_month_due:
            m.status = MemberStatus.ONE_MONTH_FOLLOWUP
            m.one_month_followup_sent = True
            audit_service.log_action(
                db=db, user_id=None, member_id=m.id,
                action="STATUS_CHANGED",
                details="System: one-month follow-up due, status set to ONE_MONTH_FOLLOWUP",
            )
        db.commit()

        if one_month_due:
            names = ", ".join(f"{m.first_name} {m.last_name}" for m in one_month_due)
            send_notification(
                settings.FOLLOWUP_NOTIFICATION_EMAIL,
                "One month follow-up needed",
                f"The following member(s) need a one month followup: {names}. "
                f"Their status has been set to \"1-Month Followup\" in the signup manager.",
            )
            logger.info("One-month follow-up triggered for %d member(s)", len(one_month_due))

        # --- Six-month follow-up: 6 months after entering IN_SIGNAL ---
        six_month_due = db.query(Member).filter(
            Member.status == MemberStatus.IN_SIGNAL,
            Member.resting_since != None,
            Member.resting_since <= now - SIX_MONTHS,
        ).all()

        for m in six_month_due:
            m.status = MemberStatus.SIX_MONTH_FOLLOWUP
            audit_service.log_action(
                db=db, user_id=None, member_id=m.id,
                action="STATUS_CHANGED",
                details="System: six-month follow-up due, status set to SIX_MONTH_FOLLOWUP",
            )
        db.commit()

        if six_month_due:
            names = ", ".join(f"{m.first_name} {m.last_name}" for m in six_month_due)
            send_notification(
                settings.FOLLOWUP_NOTIFICATION_EMAIL,
                "Six month follow-up needed",
                f"The following member(s) need a six month followup: {names}. "
                f"Their status has been set to \"6-Month Followup\" in the signup manager. "
                f"After checking in, set them back to \"In Signal\" and they will "
                f"resurface in another six months.",
            )
            logger.info("Six-month follow-up triggered for %d member(s)", len(six_month_due))
    finally:
        db.close()
