from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
from app.database import get_db
from app.models.user import User, UserRole
from app.models.member import Member, MemberStatus
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth import verify_password, create_access_token
from app.services.audit import audit_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Stale assignment threshold (7 days)
STALE_ASSIGNMENT_DAYS = 7


def reclaim_stale_assignments(db: Session) -> int:
    """
    Find members that have been assigned for more than STALE_ASSIGNMENT_DAYS
    and reset them to PENDING status so they can be picked up by other vetters.
    Returns the number of members reclaimed.
    """
    stale_threshold = datetime.utcnow() - timedelta(days=STALE_ASSIGNMENT_DAYS)

    # Find members assigned but not completed within the threshold
    stale_members = db.query(Member).filter(
        Member.status == MemberStatus.ASSIGNED,
        Member.updated_at < stale_threshold
    ).all()

    reclaimed_count = 0
    for member in stale_members:
        old_vetter_id = member.assigned_vetter_id
        member.status = MemberStatus.PENDING
        member.assigned_vetter_id = None

        # Log the reclamation
        audit_service.log_action(
            db=db,
            user_id=None,  # System action
            member_id=member.id,
            action="ASSIGNMENT_RECLAIMED",
            details=f"Assignment reclaimed from vetter {old_vetter_id} after {STALE_ASSIGNMENT_DAYS} days of inactivity"
        )
        reclaimed_count += 1

    if reclaimed_count > 0:
        db.commit()

    return reclaimed_count


def auto_assign_next_member(db: Session, vetter_id: int) -> Optional[Member]:
    """
    Auto-assign the next pending member to a vetter.
    First reclaims any stale assignments, then assigns the next pending member.
    Returns the assigned member or None if no pending members.
    """
    # Reclaim stale assignments before assigning new ones
    reclaimed = reclaim_stale_assignments(db)
    if reclaimed > 0:
        # Log that we reclaimed some assignments (for monitoring)
        audit_service.log_action(
            db=db,
            user_id=vetter_id,
            member_id=None,
            action="STALE_CHECK",
            details=f"Reclaimed {reclaimed} stale assignment(s) during auto-assignment"
        )

    # Get the first pending member (oldest first)
    next_member = db.query(Member).filter(
        Member.status == MemberStatus.PENDING
    ).order_by(Member.created_at.asc()).first()

    if next_member:
        next_member.assigned_vetter_id = vetter_id
        next_member.status = MemberStatus.ASSIGNED

        # Log the auto-assignment
        audit_service.log_action(
            db=db,
            user_id=vetter_id,
            member_id=next_member.id,
            action="AUTO_ASSIGNED",
            details=f"Automatically assigned to vetter"
        )

        db.commit()
        db.refresh(next_member)

    return next_member


@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and return JWT token."""
    user = db.query(User).filter(User.username == credentials.username).first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Auto-assign next pending member to vetter on login
    if user.role == UserRole.VETTER:
        auto_assign_next_member(db, user.id)

    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        user_id=user.id,
        username=user.username,
        role=user.role.value,
        full_name=user.full_name
    )
