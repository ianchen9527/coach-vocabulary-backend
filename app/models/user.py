from sqlalchemy import String, Integer, ForeignKey, Boolean, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, Optional
from datetime import datetime

from app.models.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.word_progress import WordProgress
    from app.models.word_level import WordLevel
    from app.models.word_category import WordCategory
    from app.models.answer_history import AnswerHistory


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    username: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    current_level_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("word_levels.id"),
        nullable=True
    )
    current_category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("word_categories.id"),
        nullable=True
    )

    # Partial unique index: email must be unique only among active users
    # This allows deleted users' emails to be reused for new registrations
    __table_args__ = (
        Index(
            'ix_users_email_active',
            'email',
            unique=True,
            postgresql_where=(is_active == True)
        ),
    )

    # Relationships
    word_progress: Mapped[list["WordProgress"]] = relationship(
        "WordProgress",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    current_level: Mapped[Optional["WordLevel"]] = relationship("WordLevel", back_populates="users")
    current_category: Mapped[Optional["WordCategory"]] = relationship("WordCategory", back_populates="users")
    answer_history: Mapped[list["AnswerHistory"]] = relationship(
        "AnswerHistory",
        back_populates="user",
        cascade="all, delete-orphan"
    )
