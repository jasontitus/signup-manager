from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.user import User, UserRole
from app.models.member import Member, MemberStatus
from app.schemas.member import (
    MemberResponse,
    MemberDetailResponse,
    MemberUpdate,
    MemberNote
)
from app.dependencies import get_current_user, require_admin, check_member_access
from app.services.audit import audit_service
from app.routers.auth import auto_assign_next_member, reclaim_stale_assignments

router = APIRouter(prefix="/members", tags=["Members"])


@router.get("", response_model=List[MemberResponse])
def list_members(
    status_filter: Optional[MemberStatus] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List members with RBAC filtering.
    Admins see all members.
    Vetters see only assigned members.
    """
    query = db.query(Member)

    # CRITICAL: Vetter isolation - only show assigned members
    if current_user.role == UserRole.VETTER:
        query = query.filter(Member.assigned_vetter_id == current_user.id)

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
                or q_lower in member.zip_code.lower()):
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

        # Log status change
        audit_service.log_action(
            db=db,
            user_id=current_user.id,
            member_id=member.id,
            action="STATUS_CHANGED",
            details=f"Status changed from {old_status} to {update.status}"
        )

        # Auto-assign next member if vetter completed vetting
        if (current_user.role == UserRole.VETTER and
            update.status in [MemberStatus.VETTED, MemberStatus.REJECTED]):
            auto_assign_next_member(db, current_user.id)

    db.commit()
    db.refresh(member)

    return member


@router.post("/{member_id}/notes", response_model=MemberResponse)
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
    if current_user.role != UserRole.VETTER:
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
