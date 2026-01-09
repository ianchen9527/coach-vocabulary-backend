from sqlalchemy import String, Text, DateTime, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, Optional
from datetime import datetime

from app.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from app.models.word_progress import WordProgress
    from app.models.word_level import WordLevel
    from app.models.word_category import WordCategory


class Word(Base, UUIDMixin):
    __tablename__ = "words"

    word: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )
    translation: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )
    sentence: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    sentence_zh: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    image_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )
    audio_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )
    level_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("word_levels.id"),
        nullable=True
    )
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("word_categories.id"),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    # Relationships
    word_progress: Mapped[list["WordProgress"]] = relationship(
        "WordProgress",
        back_populates="word",
        cascade="all, delete-orphan"
    )
    level: Mapped["WordLevel"] = relationship("WordLevel", back_populates="words")
    category: Mapped["WordCategory"] = relationship("WordCategory", back_populates="words")
