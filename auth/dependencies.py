"""
FastAPI dependencies for authentication.
Extracts JWT from cookies/headers and returns the current user.
"""

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from database import get_db
from database.models.user import User
from auth.security import decode_access_token


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """
    Dependency: extracts JWT from cookie or Authorization header,
    validates it, and returns the User object.
    """
    token = request.cookies.get("access_token")

    # Fallback to Authorization header
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    return user


def get_optional_user(request: Request, db: Session = Depends(get_db)):
    """Dependency: returns user if authenticated, None otherwise (for public pages)."""
    try:
        return get_current_user(request, db)
    except HTTPException:
        return None
