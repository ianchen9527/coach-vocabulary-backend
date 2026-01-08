from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.word import Word
from app.models.word_progress import WordProgress
from app.utils.constants import (
    DAILY_LEARN_LIMIT,
    P1_UPCOMING_LIMIT,
    PRACTICE_MIN_WORDS,
    REVIEW_MIN_WORDS,
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
        """Get all progress records for a user (excludes P0)."""
        return (
            self.db.query(WordProgress)
            .options(joinedload(WordProgress.word))
            .filter(WordProgress.user_id == user_id)
            .all()
        )

    def get_p0_words(self, user_id: UUID, limit: Optional[int] = None) -> List[Word]:
        """
        Get P0 words (words without any progress record for this user).
        """
        # Subquery to get word_ids that have progress for this user
        learned_word_ids = (
            self.db.query(WordProgress.word_id)
            .filter(WordProgress.user_id == user_id)
            .subquery()
        )

        # Get words not in the learned list
        query = (
            self.db.query(Word)
            .filter(Word.id.notin_(learned_word_ids))
            .order_by(Word.id)
        )

        if limit:
            query = query.limit(limit)

        return query.all()

    def count_p0_words(self, user_id: UUID) -> int:
        """Count P0 words (words without any progress record for this user)."""
        learned_word_ids = (
            self.db.query(WordProgress.word_id)
            .filter(WordProgress.user_id == user_id)
            .subquery()
        )

        return (
            self.db.query(Word)
            .filter(Word.id.notin_(learned_word_ids))
            .count()
        )

    def get_words_in_pool(
        self, user_id: UUID, pool: str
    ) -> List[WordProgress]:
        """Get all words in a specific pool for a user."""
        if pool == "P0":
            # P0 is special - return empty list, use get_p0_words instead
            return []

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
        # Filter out P0 as it's not stored
        pools = [p for p in pools if p != "P0"]
        if not pools:
            return []

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
        if pool == "P0":
            return self.count_p0_words(user_id)

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

    def create_progress(
        self,
        user_id: UUID,
        word_id: UUID,
        pool: str,
        learned_at: Optional[datetime] = None,
        last_practice_time: Optional[datetime] = None,
        next_available_time: Optional[datetime] = None,
        is_in_review_phase: bool = False,
    ) -> WordProgress:
        """Create a new progress record."""
        progress = WordProgress(
            user_id=user_id,
            word_id=word_id,
            pool=pool,
            learned_at=learned_at,
            last_practice_time=last_practice_time,
            next_available_time=next_available_time,
            is_in_review_phase=is_in_review_phase,
        )
        self.db.add(progress)
        self.db.commit()
        self.db.refresh(progress)
        return progress

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
        Reset all progress for a user (delete all records, words go back to P0).

        Returns:
            Number of words reset
        """
        count = (
            self.db.query(WordProgress)
            .filter(WordProgress.user_id == user_id)
            .delete()
        )
        self.db.commit()
        return count

    def get_pool_summary(self, user_id: UUID) -> Dict[str, List[Dict[str, Any]]]:
        """Get all words grouped by pool."""
        # Get all progress records (P1-P6, R1-R5)
        all_progress = self.get_user_progress(user_id)

        pools: Dict[str, List[Dict[str, Any]]] = {
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

        # Get P0 words (no progress record)
        p0_words = self.get_p0_words(user_id)
        for word in p0_words:
            pools["P0"].append({
                "word_id": str(word.id),
                "word": word.word,
                "translation": word.translation,
                "next_available_time": None,
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
        p0_count = self.count_p0_words(user_id)
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
