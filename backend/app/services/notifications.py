"""Email notifications via Resend. All sends are fire-and-forget:
failures are logged but never block the triggering operation."""
import logging
import resend
from app.config import settings

logger = logging.getLogger(__name__)


def send_notification(to: str, subject: str, text: str) -> bool:
    """Send a notification email. `to` may be comma-separated.
    Returns True if the email was sent (or at least handed to Resend)."""
    if not settings.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not configured; skipping email %r to %s", subject, to)
        return False
    try:
        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send({
            "from": settings.EMAIL_FROM_ADDRESS,
            "to": [e.strip() for e in to.split(",") if e.strip()],
            "subject": subject,
            "text": text,
        })
        return True
    except Exception as e:
        logger.error("Failed to send notification email %r to %s: %s", subject, to, e)
        return False


def notify_status_change(member_names: list, new_status) -> None:
    """Notify the vetting contact when members are marked VETTED or
    NEEDS_FOLLOW_UP. `member_names` is a list of full-name strings."""
    from app.models.member import MemberStatus

    if not member_names:
        return
    names = ", ".join(member_names)
    if new_status == MemberStatus.VETTED:
        plural = "people have" if len(member_names) > 1 else "person has"
        send_notification(
            settings.VETTING_NOTIFICATION_EMAIL,
            "New member vetted",
            f"A new {plural} been vetted: {names}",
        )
    elif new_status == MemberStatus.NEEDS_FOLLOW_UP:
        plural = "members have" if len(member_names) > 1 else "member has"
        send_notification(
            settings.VETTING_NOTIFICATION_EMAIL,
            "Member marked needs follow up",
            f"The following {plural} been marked \"needs follow up\": {names}",
        )
