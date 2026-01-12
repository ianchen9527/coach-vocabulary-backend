from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.admin import (
    ResetProgressResponse,
    ResetCooldownResponse,
    SeedWordsRequest,
    SeedWordsResponse,
    WordsListResponse,
    WordOutput,
)
from app.repositories.progress_repository import ProgressRepository
from app.repositories.word_repository import WordRepository
from app.repositories.user_repository import UserRepository

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/reset-progress", response_model=ResetProgressResponse)
def reset_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reset all learning progress for a user (all words back to P0)."""
    progress_repo = ProgressRepository(db)

    words_reset = progress_repo.reset_user_progress(current_user.id)

    return ResetProgressResponse(
        success=True,
        words_reset=words_reset,
    )


@router.post("/reset-cooldown", response_model=ResetCooldownResponse)
def reset_cooldown(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reset all cooldown times for a user (set next_available_time to now).

    This is a debug/test helper to skip waiting periods.
    After calling this, all words in P1-P5 and R1-R5 will be immediately available.
    """
    progress_repo = ProgressRepository(db)

    words_affected = progress_repo.reset_cooldown(current_user.id)

    return ResetCooldownResponse(
        success=True,
        words_affected=words_affected,
    )


@router.post("/seed-words", response_model=SeedWordsResponse)
def seed_words(
    request: SeedWordsRequest,
    db: Session = Depends(get_db)
):
    """Import words into the database."""
    word_repo = WordRepository(db)
    user_repo = UserRepository(db)
    progress_repo = ProgressRepository(db)

    if request.clear_existing:
        word_repo.delete_all()

    # Convert to dict for bulk create
    words_data = [w.model_dump() for w in request.words]
    imported, skipped = word_repo.bulk_create(words_data)

    # Note: New words will be picked up when users call /api/auth/login
    # or we could add logic here to initialize progress for existing users

    return SeedWordsResponse(
        success=True,
        words_imported=imported,
        words_skipped=skipped,
    )


@router.get("/words", response_model=WordsListResponse)
def get_all_words(db: Session = Depends(get_db)):
    """Get all words in the database."""
    word_repo = WordRepository(db)

    words = word_repo.get_all()
    total_count = len(words)

    return WordsListResponse(
        words=[
            WordOutput(
                id=str(w.id),
                word=w.word,
                translation=w.translation,
                sentence=w.sentence,
                sentence_zh=w.sentence_zh,
                image_url=w.image_url,
                audio_url=w.audio_url,
                created_at=w.created_at,
            )
            for w in words
        ],
        total_count=total_count,
    )
