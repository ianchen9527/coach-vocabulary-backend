from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.word import Word
    from app.models.user import User


class WordCategory(Base):
    __tablename__ = "word_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    label: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    order: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)

    # Relationships
    words: Mapped[list["Word"]] = relationship("Word", back_populates="category")
    users: Mapped[list["User"]] = relationship("User", back_populates="current_category")
