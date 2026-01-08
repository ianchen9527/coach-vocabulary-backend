from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_user_id
from app.schemas.learn import (
    LearnSessionResponse,
    LearnCompleteRequest,
    LearnCompleteResponse,
)
from app.schemas.common import WordDetailSchema, ExerciseSchema, OptionSchema
from app.repositories.progress_repository import ProgressRepository
from app.repositories.word_repository import WordRepository
from app.services.session_service import build_learn_exercise, build_word_detail
from app.services.spaced_repetition import get_next_available_time
from app.utils.constants import LEARN_SESSION_SIZE

router = APIRouter(prefix="/api/learn", tags=["learn"])


@router.get("/session", response_model=LearnSessionResponse)
def get_learn_session(
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    """Get a learning session with 5 new words."""
    progress_repo = ProgressRepository(db)
    word_repo = WordRepository(db)

    # Check if can learn
    can_learn, reason = progress_repo.can_learn(user_id)
    if not can_learn:
        return LearnSessionResponse(
            available=False,
            reason=reason,
            words=[],
            exercises=[],
        )

    # Get P0 words for this session (words without progress records)
    p0_words = progress_repo.get_p0_words(user_id, limit=LEARN_SESSION_SIZE)

    if not p0_words:
        return LearnSessionResponse(
            available=False,
            reason="no_words_in_p0",
            words=[],
            exercises=[],
        )

    # Get all words for generating options
    all_words = word_repo.get_all()

    # Build word details and exercises
    words = []
    exercises = []

    for word in p0_words:
        words.append(WordDetailSchema(**build_word_detail(word)))

        # Build exercise
        exercise_data = build_learn_exercise(word, all_words, p0_words)
        exercises.append(ExerciseSchema(
            word_id=exercise_data["word_id"],
            type=exercise_data["type"],
            options=[OptionSchema(**opt) for opt in exercise_data["options"]],
            correct_index=exercise_data["correct_index"],
        ))

    return LearnSessionResponse(
        available=True,
        reason=None,
        words=words,
        exercises=exercises,
    )


@router.post("/complete", response_model=LearnCompleteResponse)
def complete_learn(
    request: LearnCompleteRequest,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    """Complete learning session, move words from P0 to P1."""
    progress_repo = ProgressRepository(db)
    word_repo = WordRepository(db)

    now = datetime.now(timezone.utc)
    next_time = get_next_available_time("P1")
    words_moved = 0

    for word_id_str in request.word_ids:
        try:
            word_id = UUID(word_id_str)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid word_id: {word_id_str}")

        # Check if word exists
        word = word_repo.get_by_id(word_id)
        if not word:
            raise HTTPException(status_code=404, detail=f"Word not found: {word_id_str}")

        # Check if already has progress record (not in P0)
        existing_progress = progress_repo.get_by_user_and_word(user_id, word_id)
        if existing_progress:
            raise HTTPException(status_code=400, detail=f"Word {word_id_str} is not in P0 pool")

        # Create new progress record for P1
        progress_repo.create_progress(
            user_id=user_id,
            word_id=word_id,
            pool="P1",
            learned_at=now,
            last_practice_time=now,
            next_available_time=next_time,
        )
        words_moved += 1

    today_learned = progress_repo.count_today_learned(user_id)

    return LearnCompleteResponse(
        success=True,
        words_moved=words_moved,
        today_learned=today_learned,
    )
