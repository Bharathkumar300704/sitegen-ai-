"""
Auth service — business logic for authentication.
"""

from sqlalchemy.orm import Session
from repositories import auth_repository
from auth.security import verify_password, create_access_token
from config.logging_config import get_logger

logger = get_logger(__name__)


class AuthService:

    @staticmethod
    def register(db: Session, email: str, username: str, password: str, full_name: str = None):
        """Register a new user. Raises ValueError on duplicate."""
        # Check for existing email
        if auth_repository.get_user_by_email(db, email):
            raise ValueError("Email already registered")

        # Check for existing username
        if auth_repository.get_user_by_username(db, username):
            raise ValueError("Username already taken")

        user = auth_repository.create_user(db, email, username, password, full_name)
        logger.info(f"New user registered: {email}")
        return user

    @staticmethod
    def login(db: Session, email: str, password: str) -> dict:
        """Authenticate user and return token. Raises ValueError on failure."""
        user = auth_repository.get_user_by_email(db, email)
        if not user:
            raise ValueError("Invalid email or password")

        if not verify_password(password, user.hashed_password):
            raise ValueError("Invalid email or password")

        if not user.is_active:
            raise ValueError("Account is disabled")

        token = create_access_token(data={"sub": user.id, "email": user.email})
        logger.info(f"User logged in: {email}")
        return {"access_token": token, "user": user}

    @staticmethod
    def change_password(db: Session, user, current_password: str, new_password: str):
        """Change user's password. Validates current password first."""
        if not verify_password(current_password, user.hashed_password):
            raise ValueError("Current password is incorrect")
        auth_repository.update_password(db, user, new_password)
        logger.info(f"Password changed for user: {user.email}")
