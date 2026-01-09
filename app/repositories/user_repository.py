from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: UUID) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()

    def create(self, username: str) -> User:
        user = User(username=username)
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

    def get_or_create(self, username: str) -> tuple[User, bool]:
        """
        Get existing user or create new one.

        Returns:
            tuple: (user, is_new_user)
        """
        user = self.get_by_username(username)
        if user:
            return user, False

        user = self.create(username)
        return user, True
