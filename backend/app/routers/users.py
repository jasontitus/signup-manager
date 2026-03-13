from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.services.auth import hash_password
from app.dependencies import require_admin, ADMIN_ROLES

router = APIRouter(prefix="/users", tags=["Users"])


def _check_role_permission(current_user: User, target_role: UserRole):
    """
    Enforce role hierarchy for user management.
    GROUP_ADMIN can only create/assign the VETTER role.
    SUPER_ADMIN can assign any role.
    """
    if current_user.role == UserRole.GROUP_ADMIN and target_role != UserRole.VETTER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Group admins can only manage vetter accounts"
        )


@router.get("", response_model=List[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """List all users (admin only)."""
    users = db.query(User).all()
    return users


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create a new user (admin only). GROUP_ADMIN can only create vetters."""
    _check_role_permission(current_user, user_data.role)

    # Check if username already exists
    existing = db.query(User).filter(User.username == user_data.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists"
        )

    user = User(
        username=user_data.username,
        hashed_password=hash_password(user_data.password),
        role=user_data.role,
        full_name=user_data.full_name,
        is_active=True
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get a specific user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update a user (admin only). GROUP_ADMIN can only edit vetters."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # GROUP_ADMIN cannot edit non-vetter users
    if current_user.role == UserRole.GROUP_ADMIN and user.role != UserRole.VETTER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Group admins can only manage vetter accounts"
        )

    # If changing role, enforce hierarchy
    if user_data.role:
        _check_role_permission(current_user, user_data.role)

    if user_data.password:
        user.hashed_password = hash_password(user_data.password)
    if user_data.role:
        user.role = user_data.role
    if user_data.full_name:
        user.full_name = user_data.full_name
    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    db.commit()
    db.refresh(user)

    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete a user (admin only). GROUP_ADMIN can only delete vetters."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Prevent deleting yourself
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    # GROUP_ADMIN cannot delete non-vetter users
    if current_user.role == UserRole.GROUP_ADMIN and user.role != UserRole.VETTER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Group admins can only manage vetter accounts"
        )

    db.delete(user)
    db.commit()

    return None
