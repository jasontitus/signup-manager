from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserRole
from app.models.member import Member
from app.services.auth import verify_token

security = HTTPBearer()

# Roles that have admin-level access (can see all members, access admin dashboard)
ADMIN_ROLES = {UserRole.SUPER_ADMIN, UserRole.GROUP_ADMIN}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Dependency to get the current authenticated user from JWT token."""
    token = credentials.credentials
    payload = verify_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to require admin-level role (SUPER_ADMIN or GROUP_ADMIN)."""
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to require SUPER_ADMIN role specifically."""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    return current_user


def check_member_access(member: Member, user: User) -> bool:
    """
    Check if a user has access to view/edit a member.
    Admins (SUPER_ADMIN and GROUP_ADMIN) can access all members.
    Vetters can only access members assigned to them.
    """
    if user.role in ADMIN_ROLES:
        return True

    if user.role == UserRole.VETTER:
        return member.assigned_vetter_id == user.id

    return False
