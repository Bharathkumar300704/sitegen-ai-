"""
Authentication API routes — register, login, logout, profile.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session
from database import get_db
from schemas.user_schema import UserRegister, UserLogin, UserResponse
from services.auth_service import AuthService
from auth.dependencies import get_current_user
from database.models.user import User

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse)
def register(data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user account."""
    try:
        user = AuthService.register(
            db, email=data.email, username=data.username,
            password=data.password, full_name=data.full_name,
        )
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
def login(data: UserLogin, response: Response, db: Session = Depends(get_db)):
    """Login and receive JWT token (set as cookie)."""
    try:
        result = AuthService.login(db, email=data.email, password=data.password)
        # Set JWT as HTTP-only cookie
        response.set_cookie(
            key="access_token",
            value=result["access_token"],
            httponly=True,
            max_age=3600,
            samesite="lax",
        )
        return {
            "message": "Login successful",
            "access_token": result["access_token"],
            "user": UserResponse.model_validate(result["user"]),
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/logout")
def logout(response: Response):
    """Logout by clearing the access token cookie."""
    response.delete_cookie("access_token")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
def get_profile(user: User = Depends(get_current_user)):
    """Get the currently authenticated user's profile."""
    return user
