import csv
import io
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.user import User, UserRole
from app.models.member import Member, MemberStatus
from app.schemas.member import (
    MemberResponse,
    MemberDetailResponse,
    MemberUpdate,
    MemberNote,
    MemberTagsUpdate,
    MemberArchiveUpdate,
    MemberCustomFieldsUpdate,
    MemberContactResponse,
    BulkStatusUpdate,
    BulkArchiveUpdate,
    BulkTagUpdate,
)
from app.dependencies import get_current_user, require_admin, check_member_access, ADMIN_ROLES
from app.services.audit import audit_service
from app.services.notifications import notify_status_change
from app.routers.auth import auto_assign_next_member, reclaim_stale_assignments

router = APIRouter(prefix="/members", tags=["Members"])


def apply_status_timestamps(member: Member, new_status: MemberStatus):
    """Update follow-up scheduling anchors when a member's status changes.
    VETTED starts the one-month follow-up timer; IN_SIGNAL (the resting
    status) starts/restarts the recurring six-month follow-up timer."""
    if new_status == MemberStatus.VETTED:
        member.vetted_at = datetime.utcnow()
        member.one_month_followup_sent = False
    elif new_status == MemberStatus.IN_SIGNAL:
        member.resting_since = datetime.utcnow()


@router.get("", response_model=List[MemberResponse])
def list_members(
    status_filter: Optional[MemberStatus] = Query(None),
    include_archived: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List members with RBAC filtering.
    Admins see all members.
    Vetters see only assigned members.
    By default, archived members are hidden unless include_archived=True.
    """
    query = db.query(Member)

    # CRITICAL: Vetter isolation - only show assigned members
    if current_user.role not in ADMIN_ROLES:
        query = query.filter(Member.assigned_vetter_id == current_user.id)

    # Hide archived by default
    if not include_archived:
        query = query.filter(Member.archived == False)

    # Optional status filter
    if status_filter:
        query = query.filter(Member.status == status_filter)

    members = query.order_by(Member.created_at.desc()).all()
    return members


@router.get("/search/query", response_model=List[MemberResponse])
def search_members(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Search members by name, location, notes, or custom fields.
    All PII fields are encrypted, so search is done in-memory after decryption.
    Notes are searched via DB query (not encrypted).
    """
    # Log the search in audit log
    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        member_id=None,
        action="SEARCHED_MEMBERS",
        details=f"Query: {q}"
    )

    # Get base query with RBAC filtering
    base_query = db.query(Member)
    if current_user.role == UserRole.VETTER:
        base_query = base_query.filter(Member.assigned_vetter_id == current_user.id)

    # Notes are not encrypted — search via DB for efficiency
    search_term = f"%{q}%"
    note_matches = set(
        m.id for m in base_query.filter(Member.notes.ilike(search_term)).all()
    )

    # All PII is encrypted — search in-memory after decryption
    all_members = base_query.all()
    q_lower = q.lower()
    matches = []

    for member in all_members:
        # Already matched by notes query
        if member.id in note_matches:
            matches.append(member)
            continue

        # Search decrypted PII fields
        if (q_lower in member.first_name.lower()
                or q_lower in member.last_name.lower()
                or q_lower in member.city.lower()
                or q_lower in member.zip_code.lower()
                or q_lower in member.street_address.lower()):
            matches.append(member)
            continue

        # Search custom fields
        try:
            custom_fields = member.custom_fields
            for field_value in custom_fields.values():
                if field_value and q_lower in str(field_value).lower():
                    matches.append(member)
                    break
        except Exception as e:
            print(f"Error searching custom fields for member {member.id}: {e}")

    # Sort by creation date (newest first)
    matches.sort(key=lambda m: m.created_at, reverse=True)

    return matches


@router.get("/contacts", response_model=List[MemberContactResponse])
def get_contacts(
    status_filter: Optional[MemberStatus] = Query(None),
    tag_category: Optional[str] = Query(None),
    tag_value: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get contact list with decrypted PII for filtered members (admin only).
    Returns name, email, phone, city, zip, status, tags.
    """
    query = db.query(Member)

    if status_filter:
        query = query.filter(Member.status == status_filter)

    members = query.order_by(Member.created_at.desc()).all()

    # Filter by tag in-memory (tags are stored as JSON)
    if tag_category and tag_value:
        filtered = []
        for m in members:
            tags = m.tags or {}
            tag_val = tags.get(tag_category)
            if isinstance(tag_val, list):
                if tag_value in tag_val:
                    filtered.append(m)
            elif tag_val == tag_value:
                filtered.append(m)
        members = filtered

    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        member_id=None,
        action="VIEWED_CONTACT_LIST",
        details=f"Admin viewed contact list ({len(members)} members, filters: status={status_filter}, tag={tag_category}:{tag_value})"
    )

    return members


EXPORTABLE_FIELDS = {
    "first_name": "First Name",
    "last_name": "Last Name",
    "email": "Email",
    "phone_number": "Phone",
    "street_address": "Street Address",
    "city": "City",
    "zip_code": "Zip Code",
    "status": "Status",
    "tags": "Tags",
    "notes": "Notes",
    "created_at": "Applied",
    "updated_at": "Updated",
}


@router.get("/export")
def export_members_csv(
    fields: str = Query(..., description="Comma-separated field names to include"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="asc or desc"),
    status_filter: Optional[MemberStatus] = Query(None),
    include_archived: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Export members as CSV with selected fields (admin only)."""
    requested_fields = [f.strip() for f in fields.split(",") if f.strip() in EXPORTABLE_FIELDS]
    if not requested_fields:
        raise HTTPException(status_code=400, detail="No valid fields specified")

    query = db.query(Member)
    if not include_archived:
        query = query.filter(Member.archived == False)
    if status_filter:
        query = query.filter(Member.status == status_filter)

    members = query.all()

    # Sort in Python (PII fields are encrypted in DB, can't sort there)
    reverse = sort_order == "desc"
    def sort_key(m):
        val = getattr(m, sort_by, "") or ""
        if isinstance(val, str):
            return val.lower()
        return val
    try:
        members.sort(key=sort_key, reverse=reverse)
    except TypeError:
        pass

    # Build CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([EXPORTABLE_FIELDS[f] for f in requested_fields])
    for m in members:
        row = []
        for f in requested_fields:
            val = getattr(m, f, "")
            if f == "tags" and isinstance(val, dict):
                val = "; ".join(f"{k}: {v}" for k, v in val.items()) if val else ""
            elif f in ("created_at", "updated_at") and val:
                val = val.strftime("%Y-%m-%d %H:%M")
            elif val is None:
                val = ""
            row.append(str(val))
        writer.writerow(row)

    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        member_id=None,
        action="EXPORTED_CSV",
        details=f"{current_user.username} exported {len(members)} members, fields: {','.join(requested_fields)}"
    )

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=members-export.csv"},
    )


@router.patch("/bulk-status", response_model=List[MemberResponse])
def bulk_update_status(
    update: BulkStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Bulk update status for multiple members (admin only)."""
    members = db.query(Member).filter(Member.id.in_(update.member_ids)).all()
    if not members:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No members found")

    for member in members:
        old_status = member.status
        member.status = update.status
        apply_status_timestamps(member, update.status)
        audit_service.log_action(
            db=db,
            user_id=current_user.id,
            member_id=member.id,
            action="STATUS_CHANGED",
            details=f"Bulk status change from {old_status} to {update.status}"
        )

    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        member_id=None,
        action="BULK_STATUS_UPDATE",
        details=f"Bulk updated {len(members)} member(s) to status {update.status}"
    )

    db.commit()
    for member in members:
        db.refresh(member)

    # Single digest email for VETTED / NEEDS_FOLLOW_UP bulk changes
    if update.status in (MemberStatus.VETTED, MemberStatus.NEEDS_FOLLOW_UP):
        names = [f"{m.first_name} {m.last_name}" for m in members]
        notify_status_change(names, update.status)

    return members


@router.patch("/bulk-archive", response_model=List[MemberResponse])
def bulk_update_archived(
    update: BulkArchiveUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Bulk update archived flag for multiple members (admin only)."""
    members = db.query(Member).filter(Member.id.in_(update.member_ids)).all()
    if not members:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No members found")

    for member in members:
        member.archived = update.archived
        audit_service.log_action(
            db=db,
            user_id=current_user.id,
            member_id=member.id,
            action="ARCHIVED_UPDATED",
            details=f"Bulk archived set to {update.archived}"
        )

    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        member_id=None,
        action="BULK_ARCHIVE_UPDATE",
        details=f"Bulk updated {len(members)} member(s) archived to {update.archived}"
    )

    db.commit()
    for member in members:
        db.refresh(member)
    return members


@router.patch("/bulk-tags", response_model=List[MemberResponse])
def bulk_update_tags(
    update: BulkTagUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Bulk set a tag category value for multiple members (admin only)."""
    members = db.query(Member).filter(Member.id.in_(update.member_ids)).all()
    if not members:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No members found")

    for member in members:
        tags = dict(member.tags or {})
        tags[update.tag_key] = update.tag_value
        member.tags = tags
        audit_service.log_action(
            db=db,
            user_id=current_user.id,
            member_id=member.id,
            action="TAGS_UPDATED",
            details=f"Bulk tag update: {update.tag_key} set to {update.tag_value}"
        )

    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        member_id=None,
        action="BULK_TAGS_UPDATE",
        details=f"Bulk updated {len(members)} member(s) tag {update.tag_key} to {update.tag_value}"
    )

    db.commit()
    for member in members:
        db.refresh(member)
    return members


@router.get("/{member_id}", response_model=MemberDetailResponse)
def get_member(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get member details with decrypted PII.
    Checks access permissions and logs audit entry.
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    # Check access permission
    if not check_member_access(member, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this member"
        )

    # Log PII access
    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        member_id=member.id,
        action="VIEWED_PII",
        details=f"User {current_user.username} viewed PII for member {member.id}"
    )

    return member




@router.patch("/{member_id}/status", response_model=MemberResponse)
def update_member_status(
    member_id: int,
    update: MemberUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update member status (admin or assigned vetter)."""
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    # Check access permission
    if not check_member_access(member, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this member"
        )

    if update.status:
        old_status = member.status
        member.status = update.status
        apply_status_timestamps(member, update.status)

        # Log status change
        audit_service.log_action(
            db=db,
            user_id=current_user.id,
            member_id=member.id,
            action="STATUS_CHANGED",
            details=f"Status changed from {old_status} to {update.status}"
        )

        # Auto-assign next member if vetter completed vetting
        if (current_user.role not in ADMIN_ROLES and
            update.status in [MemberStatus.VETTED, MemberStatus.REJECTED]):
            auto_assign_next_member(db, current_user.id)

    db.commit()
    db.refresh(member)

    # Email notification for VETTED / NEEDS_FOLLOW_UP (after commit, fire-and-forget)
    if update.status in (MemberStatus.VETTED, MemberStatus.NEEDS_FOLLOW_UP):
        notify_status_change([f"{member.first_name} {member.last_name}"], update.status)

    return member


@router.post("/{member_id}/notes", response_model=MemberDetailResponse)
def add_member_note(
    member_id: int,
    note_data: MemberNote,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a note to a member (admin or assigned vetter)."""
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    # Check access permission
    if not check_member_access(member, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to add notes to this member"
        )

    # Append note with timestamp and user
    from datetime import datetime
    timestamp = datetime.utcnow().isoformat()
    new_note = f"[{timestamp}] {current_user.username}: {note_data.note}"

    if member.notes:
        member.notes = f"{member.notes}\n\n{new_note}"
    else:
        member.notes = new_note

    # Log note addition
    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        member_id=member.id,
        action="NOTE_ADDED",
        details="Added internal note"
    )

    db.commit()
    db.refresh(member)

    return member


@router.get("/queue-count")
def get_queue_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the count of PENDING members in the queue.
    Available to vetters and admins.
    """
    count = db.query(Member).filter(Member.status == MemberStatus.PENDING).count()
    return {"pending_count": count}


@router.post("/next-candidate", response_model=Optional[MemberResponse])
def get_next_candidate(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the next pending candidate for vetting.
    Automatically assigns the next member in queue to the current vetter.
    Returns None if no pending candidates are available.
    """
    if current_user.role in ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only vetters can request next candidate"
        )

    next_member = auto_assign_next_member(db, current_user.id)

    if not next_member:
        return None

    return next_member


@router.post("/reclaim-stale")
def reclaim_stale_assignments_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Manually trigger reclamation of stale assignments (admin only).
    Members assigned for more than 7 days are reset to PENDING status.
    """
    reclaimed_count = reclaim_stale_assignments(db)

    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        member_id=None,
        action="MANUAL_STALE_RECLAIM",
        details=f"Admin manually reclaimed {reclaimed_count} stale assignment(s)"
    )

    return {
        "reclaimed_count": reclaimed_count,
        "message": f"Successfully reclaimed {reclaimed_count} stale assignment(s)"
    }


@router.patch("/{member_id}/tags", response_model=MemberDetailResponse)
def update_member_tags(
    member_id: int,
    update: MemberTagsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update member tags (admin or assigned vetter)."""
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    if not check_member_access(member, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this member"
        )

    member.tags = update.tags

    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        member_id=member.id,
        action="TAGS_UPDATED",
        details=f"Tags updated by {current_user.username}"
    )

    db.commit()
    db.refresh(member)
    return member


@router.patch("/{member_id}/custom-fields", response_model=MemberDetailResponse)
def update_custom_fields(
    member_id: int,
    update: MemberCustomFieldsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update custom fields with merge semantics (admin or assigned vetter)."""
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    if not check_member_access(member, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this member"
        )

    # Merge semantics: preserve existing fields, add/update new ones
    existing = member.custom_fields or {}
    existing.update(update.custom_fields)
    member.custom_fields = existing

    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        member_id=member.id,
        action="CUSTOM_FIELDS_UPDATED",
        details=f"Custom fields updated by {current_user.username}"
    )

    db.commit()
    db.refresh(member)
    return member


@router.patch("/{member_id}/archive", response_model=MemberDetailResponse)
def update_archived(
    member_id: int,
    update: MemberArchiveUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update archived flag (admin or assigned vetter)."""
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    if not check_member_access(member, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this member"
        )

    member.archived = update.archived

    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        member_id=member.id,
        action="ARCHIVED_UPDATED",
        details=f"Archived set to {update.archived} by {current_user.username}"
    )

    db.commit()
    db.refresh(member)
    return member


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete a member (admin only)."""
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    # Log deletion before removing the member
    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        member_id=member.id,
        action="MEMBER_DELETED",
        details=f"Admin deleted member {member.first_name} {member.last_name} (ID: {member.id})"
    )

    # Delete related audit logs first (to handle foreign key constraint)
    from app.models.audit_log import AuditLog
    db.query(AuditLog).filter(AuditLog.member_id == member_id).delete()

    # Delete the member
    db.delete(member)
    db.commit()

    return None
