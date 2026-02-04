from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.user import UserRole


class UserCreate(BaseModel):
    username: str
    password: str
    role: UserRole
    full_name: str


class UserUpdate(BaseModel):
    password: Optional[str] = None
    role: Optional[UserRole] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: int
    username: str
    role: UserRole
    full_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
