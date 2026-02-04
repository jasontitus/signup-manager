from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, Dict
from app.models.member import MemberStatus


class MemberCreate(BaseModel):
    """Schema for public application form submission (standard fields only)."""
    first_name: str
    last_name: str
    street_address: str
    city: str
    zip_code: str
    phone_number: str
    email: EmailStr


class MemberUpdate(BaseModel):
    """Schema for updating member status."""
    status: Optional[MemberStatus] = None


class MemberNote(BaseModel):
    """Schema for adding a note to a member."""
    note: str


class MemberResponse(BaseModel):
    """Schema for member list view (no PII)."""
    id: int
    first_name: str
    last_name: str
    city: str
    zip_code: str
    status: MemberStatus
    assigned_vetter_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MemberDetailResponse(BaseModel):
    """Schema for member detail view with decrypted PII."""
    id: int
    first_name: str
    last_name: str
    street_address: str
    city: str
    zip_code: str
    phone_number: str
    email: str
    custom_fields: Dict[str, str] = {}
    status: MemberStatus
    assigned_vetter_id: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
