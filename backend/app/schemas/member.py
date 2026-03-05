from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, Dict, List, Any
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


class MemberTagsUpdate(BaseModel):
    """Schema for updating member tags."""
    tags: Dict[str, Any]


class MemberArchiveUpdate(BaseModel):
    """Schema for updating archived flag."""
    archived: bool


class BulkArchiveUpdate(BaseModel):
    """Schema for bulk archive update."""
    member_ids: List[int]
    archived: bool


class MemberCustomFieldsUpdate(BaseModel):
    """Schema for updating custom fields with merge semantics."""
    custom_fields: Dict[str, str]


class BulkStatusUpdate(BaseModel):
    """Schema for bulk status update."""
    member_ids: List[int]
    status: MemberStatus


class BulkTagUpdate(BaseModel):
    """Schema for bulk tag update (merge a single tag category onto multiple members)."""
    member_ids: List[int]
    tag_key: str
    tag_value: Any


class MemberResponse(BaseModel):
    """Schema for member list view (no PII)."""
    id: int
    first_name: str
    last_name: str
    city: str
    zip_code: str
    status: MemberStatus
    archived: bool = False
    tags: Dict[str, Any] = {}
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
    archived: bool = False
    tags: Dict[str, Any] = {}
    assigned_vetter_id: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MemberContactResponse(BaseModel):
    """Schema for contact list view with decrypted PII."""
    id: int
    first_name: str
    last_name: str
    email: str
    phone_number: str
    city: str
    zip_code: str
    status: MemberStatus
    tags: Dict[str, Any] = {}

    class Config:
        from_attributes = True
