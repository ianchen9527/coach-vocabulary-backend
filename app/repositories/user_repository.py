from typing import Optional
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: UUID) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()

    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email).first()

    def create(self, email: str, username: str, hashed_password: str) -> User:
        """Create a new user."""
        user = User(
            email=email,
            username=username,
            hashed_password=hashed_password
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_level_category(self, user_id: UUID, level_id: int, category_id: int) -> User:
        """Update user's current level and category."""
        user = self.get_by_id(user_id)
        if user:
            user.current_level_id = level_id
            user.current_category_id = category_id
            self.db.commit()
            self.db.refresh(user)
        return user

    def email_exists(self, email: str) -> bool:
        """Check if email already exists for an active user."""
        return self.db.query(User).filter(
            User.email == email,
            User.is_active == True
        ).first() is not None

    def soft_delete(self, user_id: UUID) -> Optional[User]:
        """
        Soft delete a user by setting is_active=False and deleted_at timestamp.

        Returns the user if found and deleted, None otherwise.
        """
        user = self.db.query(User).filter(
            User.id == user_id,
            User.is_active == True
        ).first()
        if user:
            user.is_active = False
            user.deleted_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(user)
        return user
