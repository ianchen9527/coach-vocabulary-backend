from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session, joinedload

from app.models.word import Word
from app.models.word_progress import WordProgress
from app.utils.constants import (
    DAILY_LEARN_LIMIT,
    P1_UPCOMING_LIMIT,
    PRACTICE_MIN_WORDS,
    REVIEW_MIN_WORDS,
    REVIEW_MAX_WORDS,
    LEARN_SESSION_SIZE,
    PRACTICE_SESSION_SIZE,
)


class ProgressRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_user_and_word(
        self, user_id: UUID, word_id: UUID
    ) -> Optional[WordProgress]:
        return (
            self.db.query(WordProgress)
            .filter(
                WordProgress.user_id == user_id,
                WordProgress.word_id == word_id,
            )
            .first()
        )

    def get_user_progress(self, user_id: UUID) -> List[WordProgress]:
        """Get all progress records for a user."""
        return (
            self.db.query(WordProgress)
            .options(joinedload(WordProgress.word))
            .filter(WordProgress.user_id == user_id)
            .all()
        )

    def get_words_in_pool(
        self, user_id: UUID, pool: str
    ) -> List[WordProgress]:
        """Get all words in a specific pool for a user."""
        return (
            self.db.query(WordProgress)
            .options(joinedload(WordProgress.word))
            .filter(
                WordProgress.user_id == user_id,
                WordProgress.pool == pool,
            )
            .all()
        )

    def get_words_in_pools(
        self, user_id: UUID, pools: List[str]
    ) -> List[WordProgress]:
        """Get all words in specific pools for a user."""
        return (
            self.db.query(WordProgress)
            .options(joinedload(WordProgress.word))
            .filter(
                WordProgress.user_id == user_id,
                WordProgress.pool.in_(pools),
            )
            .all()
        )

    def count_words_in_pool(self, user_id: UUID, pool: str) -> int:
        """Count words in a specific pool."""
        return (
            self.db.query(WordProgress)
            .filter(
                WordProgress.user_id == user_id,
                WordProgress.pool == pool,
            )
            .count()
        )

    def count_today_learned(self, user_id: UUID) -> int:
        """Count words learned today."""
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return (
            self.db.query(WordProgress)
            .filter(
                WordProgress.user_id == user_id,
                WordProgress.learned_at >= today_start,
            )
            .count()
        )

    def get_available_practice_words(
        self, user_id: UUID, limit: Optional[int] = None
    ) -> List[WordProgress]:
        """
        Get words available for practice (P1-P5 where next_available_time has passed).
        """
        now = datetime.now(timezone.utc)
        query = (
            self.db.query(WordProgress)
            .options(joinedload(WordProgress.word))
            .filter(
                WordProgress.user_id == user_id,
                WordProgress.pool.in_(["P1", "P2", "P3", "P4", "P5"]),
                WordProgress.next_available_time <= now,
            )
            .order_by(WordProgress.next_available_time)
        )

        if limit:
            query = query.limit(limit)

        return query.all()

    def count_available_practice(self, user_id: UUID) -> int:
        """Count words available for practice."""
        now = datetime.now(timezone.utc)
        return (
            self.db.query(WordProgress)
            .filter(
                WordProgress.user_id == user_id,
                WordProgress.pool.in_(["P1", "P2", "P3", "P4", "P5"]),
                WordProgress.next_available_time <= now,
            )
            .count()
        )

    def get_available_review_words(
        self, user_id: UUID, limit: Optional[int] = None
    ) -> List[WordProgress]:
        """
        Get words available for review (R1-R5 in review phase where time has passed).
        """
        now = datetime.now(timezone.utc)
        query = (
            self.db.query(WordProgress)
            .options(joinedload(WordProgress.word))
            .filter(
                WordProgress.user_id == user_id,
                WordProgress.pool.in_(["R1", "R2", "R3", "R4", "R5"]),
                WordProgress.is_in_review_phase == True,
                WordProgress.next_available_time <= now,
            )
            .order_by(WordProgress.next_available_time)
        )

        if limit:
            query = query.limit(limit)

        return query.all()

    def count_available_review(self, user_id: UUID) -> int:
        """Count words available for review."""
        now = datetime.now(timezone.utc)
        return (
            self.db.query(WordProgress)
            .filter(
                WordProgress.user_id == user_id,
                WordProgress.pool.in_(["R1", "R2", "R3", "R4", "R5"]),
                WordProgress.is_in_review_phase == True,
                WordProgress.next_available_time <= now,
            )
            .count()
        )

    def get_r_pool_practice_words(
        self, user_id: UUID, limit: Optional[int] = None
    ) -> List[WordProgress]:
        """
        Get R pool words ready for practice test (not in review phase, time passed).
        """
        now = datetime.now(timezone.utc)
        query = (
            self.db.query(WordProgress)
            .options(joinedload(WordProgress.word))
            .filter(
                WordProgress.user_id == user_id,
                WordProgress.pool.in_(["R1", "R2", "R3", "R4", "R5"]),
                WordProgress.is_in_review_phase == False,
                WordProgress.next_available_time <= now,
            )
            .order_by(WordProgress.next_available_time)
        )

        if limit:
            query = query.limit(limit)

        return query.all()

    def count_r_pool_practice(self, user_id: UUID) -> int:
        """Count R pool words available for practice test."""
        now = datetime.now(timezone.utc)
        return (
            self.db.query(WordProgress)
            .filter(
                WordProgress.user_id == user_id,
                WordProgress.pool.in_(["R1", "R2", "R3", "R4", "R5"]),
                WordProgress.is_in_review_phase == False,
                WordProgress.next_available_time <= now,
            )
            .count()
        )

    def count_upcoming_24h(self, user_id: UUID) -> int:
        """Count words that will be available in the next 24 hours."""
        now = datetime.now(timezone.utc)
        future_24h = now + timedelta(hours=24)

        return (
            self.db.query(WordProgress)
            .filter(
                WordProgress.user_id == user_id,
                WordProgress.next_available_time > now,
                WordProgress.next_available_time <= future_24h,
            )
            .count()
        )

    def count_p1_upcoming(self, user_id: UUID) -> int:
        """Count P1 words that will be available within 10 minutes."""
        now = datetime.now(timezone.utc)
        future_10min = now + timedelta(minutes=10)

        return (
            self.db.query(WordProgress)
            .filter(
                WordProgress.user_id == user_id,
                WordProgress.pool == "P1",
                WordProgress.next_available_time <= future_10min,
            )
            .count()
        )

    def get_next_available_time(self, user_id: UUID) -> Optional[datetime]:
        """Get the earliest next available time for any word."""
        now = datetime.now(timezone.utc)
        result = (
            self.db.query(func.min(WordProgress.next_available_time))
            .filter(
                WordProgress.user_id == user_id,
                WordProgress.next_available_time > now,
            )
            .scalar()
        )
        return result

    def initialize_user_progress(self, user_id: UUID, words: List[Word]) -> int:
        """
        Initialize progress records for all words for a user.
        All words start in P0 pool.

        Returns:
            Number of records created
        """
        count = 0
        for word in words:
            existing = self.get_by_user_and_word(user_id, word.id)
            if not existing:
                progress = WordProgress(
                    user_id=user_id,
                    word_id=word.id,
                    pool="P0",
                )
                self.db.add(progress)
                count += 1

        self.db.commit()
        return count

    def update_progress(
        self,
        progress: WordProgress,
        pool: Optional[str] = None,
        learned_at: Optional[datetime] = None,
        last_practice_time: Optional[datetime] = None,
        next_available_time: Optional[datetime] = None,
        is_in_review_phase: Optional[bool] = None,
        review_completed_time: Optional[datetime] = None,
    ) -> WordProgress:
        """Update a progress record."""
        if pool is not None:
            progress.pool = pool
        if learned_at is not None:
            progress.learned_at = learned_at
        if last_practice_time is not None:
            progress.last_practice_time = last_practice_time
        if next_available_time is not None:
            progress.next_available_time = next_available_time
        if is_in_review_phase is not None:
            progress.is_in_review_phase = is_in_review_phase
        if review_completed_time is not None:
            progress.review_completed_time = review_completed_time

        self.db.commit()
        self.db.refresh(progress)
        return progress

    def reset_user_progress(self, user_id: UUID) -> int:
        """
        Reset all progress for a user (all words back to P0).

        Returns:
            Number of words reset
        """
        count = (
            self.db.query(WordProgress)
            .filter(WordProgress.user_id == user_id)
            .update({
                WordProgress.pool: "P0",
                WordProgress.learned_at: None,
                WordProgress.last_practice_time: None,
                WordProgress.next_available_time: None,
                WordProgress.is_in_review_phase: False,
                WordProgress.review_completed_time: None,
            })
        )
        self.db.commit()
        return count

    def get_pool_summary(self, user_id: UUID) -> Dict[str, List[Dict[str, Any]]]:
        """Get all words grouped by pool."""
        all_progress = self.get_user_progress(user_id)

        pools = {
            "P0": [], "P1": [], "P2": [], "P3": [], "P4": [], "P5": [], "P6": [],
            "R1": [], "R2": [], "R3": [], "R4": [], "R5": [],
        }

        for progress in all_progress:
            pools[progress.pool].append({
                "word_id": str(progress.word_id),
                "word": progress.word.word,
                "translation": progress.word.translation,
                "next_available_time": (
                    progress.next_available_time.isoformat()
                    if progress.next_available_time
                    else None
                ),
            })

        return pools

    def can_learn(self, user_id: UUID) -> tuple[bool, Optional[str]]:
        """
        Check if user can start a learn session.

        Returns:
            tuple: (can_learn, reason if cannot)
        """
        # Check daily limit
        today_learned = self.count_today_learned(user_id)
        if today_learned >= DAILY_LEARN_LIMIT:
            return False, "daily_limit_reached"

        # Check P1 upcoming limit
        p1_upcoming = self.count_p1_upcoming(user_id)
        if p1_upcoming >= P1_UPCOMING_LIMIT:
            return False, "p1_pool_full"

        # Check if P0 has words
        p0_count = self.count_words_in_pool(user_id, "P0")
        if p0_count == 0:
            return False, "no_words_in_p0"

        return True, None

    def can_practice(self, user_id: UUID) -> tuple[bool, Optional[str]]:
        """
        Check if user can start a practice session.
        Includes both P pool practice and R pool practice phase words.

        Returns:
            tuple: (can_practice, reason if cannot)
        """
        p_pool_available = self.count_available_practice(user_id)
        r_pool_available = self.count_r_pool_practice(user_id)
        total_available = p_pool_available + r_pool_available

        if total_available < PRACTICE_MIN_WORDS:
            return False, "not_enough_words"
        return True, None

    def can_review(self, user_id: UUID) -> tuple[bool, Optional[str]]:
        """
        Check if user can start a review session.

        Returns:
            tuple: (can_review, reason if cannot)
        """
        available = self.count_available_review(user_id)
        if available < REVIEW_MIN_WORDS:
            return False, "not_enough_words"
        return True, None
