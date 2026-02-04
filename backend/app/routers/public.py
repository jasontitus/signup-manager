from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.member import Member, MemberStatus
from app.schemas.member import MemberCreate
from app.services.blind_index import generate_blind_index

router = APIRouter(prefix="/public", tags=["Public"])


@router.post("/apply", status_code=status.HTTP_201_CREATED)
def submit_application(application: MemberCreate, db: Session = Depends(get_db)):
    """Public endpoint for submitting membership applications."""

    # Check for duplicate email using blind index
    email_index = generate_blind_index(application.email)
    existing = db.query(Member).filter(Member.email_blind_index == email_index).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An application with this email address already exists"
        )

    # Create new member (encryption happens automatically via hybrid properties)
    member = Member(
        first_name=application.first_name,
        last_name=application.last_name,
        city=application.city,
        zip_code=application.zip_code,
        status=MemberStatus.PENDING
    )

    # Set encrypted fields via hybrid properties (must be set after construction)
    member.street_address = application.street_address  # Auto-encrypted
    member.phone_number = application.phone_number  # Auto-encrypted
    member.email = application.email  # Auto-encrypted + blind index
    member.occupational_background = application.occupational_background  # Auto-encrypted
    member.know_member = application.know_member  # Auto-encrypted
    member.hoped_impact = application.hoped_impact  # Auto-encrypted

    db.add(member)
    db.commit()
    db.refresh(member)

    return {
        "message": "Application submitted successfully",
        "application_id": member.id
    }
