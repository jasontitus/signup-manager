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
    MemberAssign,
    MemberNote
)
from app.dependencies import get_current_user, require_admin, check_member_access
from app.services.audit import audit_service

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


@router.patch("/{member_id}/assign", response_model=MemberResponse)
def assign_member(
    member_id: int,
    assignment: MemberAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Assign a member to a vetter (admin only)."""
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    # Verify vetter exists
    vetter = db.query(User).filter(
        User.id == assignment.vetter_id,
        User.role == UserRole.VETTER,
        User.is_active == True
    ).first()
    if not vetter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vetter not found")

    member.assigned_vetter_id = assignment.vetter_id
    member.status = MemberStatus.ASSIGNED

    # Log assignment
    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        member_id=member.id,
        action="ASSIGNED",
        details=f"Assigned to vetter {vetter.username}"
    )

    db.commit()
    db.refresh(member)

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
