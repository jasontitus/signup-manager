from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
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
    Searches standard fields via DB query and custom fields via in-memory decryption.
    """
    # Log the search in audit log
    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        member_id=None,
        action="SEARCHED_MEMBERS",
        details=f"Query: {q}"
    )

    search_term = f"%{q}%"

    # Get base query with RBAC filtering
    base_query = db.query(Member)
    if current_user.role == UserRole.VETTER:
        base_query = base_query.filter(Member.assigned_vetter_id == current_user.id)

    # Search in standard fields including notes (DB query - fast)
    db_matches = base_query.filter(
        or_(
            Member.first_name.ilike(search_term),
            Member.last_name.ilike(search_term),
            Member.city.ilike(search_term),
            Member.zip_code.ilike(search_term),
            Member.notes.ilike(search_term)
        )
    ).all()

    # Get all members accessible to this user for custom field search
    all_members = base_query.all()

    # Search in custom fields (in-memory - slower but secure)
    custom_matches = []
    for member in all_members:
        try:
            custom_fields = member.custom_fields  # Auto-decrypts
            # Search through all custom field values
            for field_value in custom_fields.values():
                if field_value and q.lower() in str(field_value).lower():
                    custom_matches.append(member)
                    break
        except Exception as e:
            # Log error but continue searching other members
            print(f"Error searching custom fields for member {member.id}: {e}")

    # Combine and deduplicate results
    all_matches = list({m.id: m for m in (db_matches + custom_matches)}.values())

    # Sort by creation date (newest first)
    all_matches.sort(key=lambda m: m.created_at, reverse=True)

    return all_matches


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
