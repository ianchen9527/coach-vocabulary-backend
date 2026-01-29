from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.answer_history import AnswerHistory


class AnswerHistoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def count_today_completed(self, user_id: UUID) -> int:
        """Count exercises completed today (practice + review)."""
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return (
            self.db.query(AnswerHistory)
            .filter(
                AnswerHistory.user_id == user_id,
                AnswerHistory.source.in_(["practice", "review_learn", "review_practice"]),
                AnswerHistory.created_at >= today_start,
            )
            .count()
        )

    def create_answer(
        self,
        user_id: UUID,
        word_id: UUID,
        word: str,
        is_correct: bool,
        exercise_type: str,
        source: str,
        pool: str,
        user_answer: Optional[str] = None,
        response_time_ms: Optional[int] = None,
    ) -> AnswerHistory:
        """Create a single answer history record."""
        answer = AnswerHistory(
            user_id=user_id,
            word_id=word_id,
            word=word,
            is_correct=is_correct,
            exercise_type=exercise_type,
            source=source,
            pool=pool,
            user_answer=user_answer,
            response_time_ms=response_time_ms,
        )
        self.db.add(answer)
        self.db.commit()
        self.db.refresh(answer)
        return answer

    def create_answers_batch(
        self,
        answers: List[dict],
    ) -> List[AnswerHistory]:
        """
        Create multiple answer history records in batch.

        Each dict in answers should contain:
        - user_id: UUID
        - word_id: UUID
        - word: str
        - is_correct: bool
        - exercise_type: str
        - source: str
        - pool: str
        - user_answer: Optional[str]
        - response_time_ms: Optional[int]
        """
        records = []
        for data in answers:
            answer = AnswerHistory(
                user_id=data["user_id"],
                word_id=data["word_id"],
                word=data["word"],
                is_correct=data["is_correct"],
                exercise_type=data["exercise_type"],
                source=data["source"],
                pool=data["pool"],
                user_answer=data.get("user_answer"),
                response_time_ms=data.get("response_time_ms"),
            )
            self.db.add(answer)
            records.append(answer)

        self.db.commit()
        for record in records:
            self.db.refresh(record)

        return records
