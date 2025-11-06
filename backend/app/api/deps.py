"""
API Dependencies

Common dependencies for API endpoints including authentication and authorization.
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user as _get_current_user
from app.db.session import get_db
from app.models.user import User


def get_current_user(
    db: Session = Depends(get_db),
    current_user: User = Depends(_get_current_user)
) -> User:
    """
    Get the current authenticated user.
    """
    return current_user


def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Require that the current user is an admin.
    Raises HTTPException if the user is not an admin.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


def require_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Require that the current user is active.
    Raises HTTPException if the user is not active.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
    return current_user
