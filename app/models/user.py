from sqlalchemy import String, Integer, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, Optional

from app.models.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.word_progress import WordProgress
    from app.models.word_level import WordLevel
    from app.models.word_category import WordCategory


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
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
    current_level_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("word_levels.id"),
        nullable=True
    )
    current_category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("word_categories.id"),
        nullable=True
    )

    # Relationships
    word_progress: Mapped[list["WordProgress"]] = relationship(
        "WordProgress",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    current_level: Mapped[Optional["WordLevel"]] = relationship("WordLevel", back_populates="users")
    current_category: Mapped[Optional["WordCategory"]] = relationship("WordCategory", back_populates="users")
