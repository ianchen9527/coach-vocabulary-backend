from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.review import (
    ReviewSessionResponse,
    ReviewCompleteRequest,
    ReviewCompleteResponse,
    ReviewSubmitRequest,
    ReviewSubmitResponse,
    ReviewSummary,
)
from app.schemas.common import (
    WordDetailWithPoolSchema,
    ExerciseSchema,
    OptionSchema,
    AnswerResultSchema,
)
from app.repositories.progress_repository import ProgressRepository
from app.repositories.word_repository import WordRepository
from app.services.session_service import build_word_detail, build_exercise
from app.services.spaced_repetition import (
    complete_review_phase,
    process_correct_answer,
    process_incorrect_answer,
)
from app.utils.constants import REVIEW_MAX_WORDS

router = APIRouter(prefix="/api/review", tags=["review"])


@router.get("/session", response_model=ReviewSessionResponse)
def get_review_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a review session with 3-5 words in review phase."""
    progress_repo = ProgressRepository(db)
    word_repo = WordRepository(db)
    user_id = current_user.id

    # Check if can review
    can_review, reason = progress_repo.can_review(user_id)
    if not can_review:
        return ReviewSessionResponse(
            available=False,
            reason=reason,
            words=[],
            exercises=[],
        )

    # Get available review words
    available_progress = progress_repo.get_available_review_words(
        user_id, limit=REVIEW_MAX_WORDS
    )

    if not available_progress:
        return ReviewSessionResponse(
            available=False,
            reason="not_enough_words",
            words=[],
            exercises=[],
        )

    # Get all words for generating options
    all_words = word_repo.get_all()
    session_words = [p.word for p in available_progress]

    # Build word details and exercises
    words = []
    exercises = []

    for progress in available_progress:
        word = progress.word

        # Word detail with pool
        word_detail = build_word_detail(word, progress.pool)
        words.append(WordDetailWithPoolSchema(**word_detail))

        # Build exercise
        exercise_data = build_exercise(word, progress.pool, all_words, session_words)
        exercises.append(ExerciseSchema(
            word_id=exercise_data["word_id"],
            type=exercise_data["type"],
            options=[OptionSchema(**opt) for opt in exercise_data["options"]],
            correct_index=exercise_data["correct_index"],
        ))

    return ReviewSessionResponse(
        available=True,
        reason=None,
        words=words,
        exercises=exercises,
    )


@router.post("/complete", response_model=ReviewCompleteResponse)
def complete_review(
    request: ReviewCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Complete review display phase, mark words for practice phase."""
    if not request.word_ids:
        raise HTTPException(status_code=400, detail="word_ids cannot be empty")

    progress_repo = ProgressRepository(db)
    user_id = current_user.id

    now = datetime.now(timezone.utc)
    words_completed = 0
    next_practice_time = None

    for word_id_str in request.word_ids:
        try:
            word_id = UUID(word_id_str)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid word_id: {word_id_str}")

        progress = progress_repo.get_by_user_and_word(user_id, word_id)
        if not progress:
            raise HTTPException(status_code=404, detail=f"Progress not found for word: {word_id_str}")

        if not progress.pool.startswith("R"):
            raise HTTPException(status_code=400, detail=f"Word {word_id_str} is not in R pool")

        # Complete review phase
        next_time, is_review = complete_review_phase(progress.pool)

        progress_repo.update_progress(
            progress,
            last_practice_time=now,
            next_available_time=next_time,
            is_in_review_phase=is_review,
            review_completed_time=now,
        )

        words_completed += 1
        if next_practice_time is None:
            next_practice_time = next_time

    return ReviewCompleteResponse(
        success=True,
        words_completed=words_completed,
        next_practice_time=next_practice_time,
    )


@router.post("/submit", response_model=ReviewSubmitResponse)
def submit_review(
    request: ReviewSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit review test answers (R pool practice phase)."""
    progress_repo = ProgressRepository(db)
    user_id = current_user.id

    now = datetime.now(timezone.utc)
    results = []
    correct_count = 0
    incorrect_count = 0
    returned_to_p = 0

    for answer in request.answers:
        try:
            word_id = UUID(answer.word_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid word_id: {answer.word_id}")

        progress = progress_repo.get_by_user_and_word(user_id, word_id)
        if not progress:
            raise HTTPException(status_code=404, detail=f"Progress not found for word: {answer.word_id}")

        previous_pool = progress.pool

        if answer.correct:
            new_pool, next_time, is_review = process_correct_answer(previous_pool)
            correct_count += 1
            if new_pool.startswith("P"):
                returned_to_p += 1
        else:
            new_pool, next_time, is_review = process_incorrect_answer(previous_pool)
            incorrect_count += 1

        # Update progress
        progress_repo.update_progress(
            progress,
            pool=new_pool,
            last_practice_time=now,
            next_available_time=next_time,
            is_in_review_phase=is_review,
        )

        results.append(AnswerResultSchema(
            word_id=answer.word_id,
            correct=answer.correct,
            previous_pool=previous_pool,
            new_pool=new_pool,
            next_available_time=next_time,
        ))

    return ReviewSubmitResponse(
        success=True,
        results=results,
        summary=ReviewSummary(
            correct_count=correct_count,
            incorrect_count=incorrect_count,
            returned_to_p=returned_to_p,
        ),
    )
