"""
Auth repository — database operations for user authentication.
"""

from sqlalchemy.orm import Session
from database.models.user import User
from auth.security import hash_password


def create_user(db: Session, email: str, username: str, password: str, full_name: str = None) -> User:
    """Create a new user with hashed password."""
    user = User(
        email=email,
        username=username,
        hashed_password=hash_password(password),
        full_name=full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_email(db: Session, email: str) -> User | None:
    """Find a user by email address."""
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str) -> User | None:
    """Find a user by username."""
    return db.query(User).filter(User.username == username).first()


def get_user_by_id(db: Session, user_id: str) -> User | None:
    """Find a user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def update_user(db: Session, user: User, **kwargs) -> User:
    """Update user fields."""
    for key, value in kwargs.items():
        if hasattr(user, key) and value is not None:
            setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


def update_password(db: Session, user: User, new_password: str) -> User:
    """Update user's password."""
    user.hashed_password = hash_password(new_password)
    db.commit()
    db.refresh(user)
    return user
