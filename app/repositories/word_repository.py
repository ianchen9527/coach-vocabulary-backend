from typing import List, Optional
from uuid import UUID
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.word import Word


class WordRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, word_id: UUID) -> Optional[Word]:
        return self.db.query(Word).filter(Word.id == word_id).first()

    def get_by_ids(self, word_ids: List[UUID]) -> List[Word]:
        return self.db.query(Word).filter(Word.id.in_(word_ids)).all()

    def get_by_word(self, word: str) -> Optional[Word]:
        return self.db.query(Word).filter(Word.word == word).first()

    def get_all(self) -> List[Word]:
        return self.db.query(Word).all()

    def count(self) -> int:
        return self.db.query(Word).count()

    def get_random_words_by_level(self, level_id: int, limit: int) -> List[Word]:
        return (
            self.db.query(Word)
            .filter(Word.level_id == level_id)
            .order_by(func.random())
            .limit(limit)
            .all()
        )

    def create(
        self,
        word: str,
        translation: str,
        sentence: Optional[str] = None,
        sentence_zh: Optional[str] = None,
        image_url: Optional[str] = None,
        audio_url: Optional[str] = None,
        level_id: Optional[int] = None,
        category_id: Optional[int] = None,
    ) -> Word:
        word_obj = Word(
            word=word,
            translation=translation,
            sentence=sentence,
            sentence_zh=sentence_zh,
            image_url=image_url,
            audio_url=audio_url,
            level_id=level_id,
            category_id=category_id,
        )
        self.db.add(word_obj)
        self.db.commit()
        self.db.refresh(word_obj)
        return word_obj

    def bulk_create(self, words_data: List[dict]) -> tuple[int, int]:
        """
        Bulk create words, skipping existing ones.

        Returns:
            tuple: (imported_count, skipped_count)
        """
        imported = 0
        skipped = 0

        for data in words_data:
            existing = self.get_by_word(data["word"])
            if existing:
                skipped += 1
                continue

            word_obj = Word(
                word=data["word"],
                translation=data["translation"],
                sentence=data.get("sentence"),
                sentence_zh=data.get("sentence_zh"),
                image_url=data.get("image_url"),
                audio_url=data.get("audio_url"),
                level_id=data.get("level_id"),
                category_id=data.get("category_id"),
            )
            self.db.add(word_obj)
            imported += 1

        self.db.commit()
        return imported, skipped

    def delete_all(self) -> int:
        """Delete all words and return count."""
        count = self.db.query(Word).count()
        self.db.query(Word).delete()
        self.db.commit()
        return count
