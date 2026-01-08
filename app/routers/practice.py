from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_user_id
from app.schemas.practice import (
    PracticeSessionResponse,
    PracticeSubmitRequest,
    PracticeSubmitResponse,
    PracticeSummary,
)
from app.schemas.common import ExerciseWithWordSchema, OptionSchema, AnswerResultSchema
from app.repositories.progress_repository import ProgressRepository
from app.repositories.word_repository import WordRepository
from app.services.session_service import (
    build_exercise,
    sort_exercises_by_type,
    get_exercise_order,
)
from app.services.spaced_repetition import (
    process_correct_answer,
    process_incorrect_answer,
)
from app.utils.constants import PRACTICE_SESSION_SIZE

router = APIRouter(prefix="/api/practice", tags=["practice"])


@router.get("/session", response_model=PracticeSessionResponse)
def get_practice_session(
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    """Get a practice session with 5 words."""
    progress_repo = ProgressRepository(db)
    word_repo = WordRepository(db)

    # Check if can practice
    can_practice, reason = progress_repo.can_practice(user_id)
    if not can_practice:
        return PracticeSessionResponse(
            available=False,
            reason=reason,
            exercises=[],
            exercise_order=[],
        )

    # Get available practice words from P pools
    p_pool_progress = progress_repo.get_available_practice_words(user_id)

    # Get available practice words from R pools (practice phase, not review phase)
    r_pool_progress = progress_repo.get_r_pool_practice_words(user_id)

    # Combine and limit
    available_progress = (p_pool_progress + r_pool_progress)[:PRACTICE_SESSION_SIZE]

    if len(available_progress) < PRACTICE_SESSION_SIZE:
        return PracticeSessionResponse(
            available=False,
            reason="not_enough_words",
            exercises=[],
            exercise_order=[],
        )

    # Get all words for generating options
    all_words = word_repo.get_all()
    session_words = [p.word for p in available_progress]

    # Build exercises
    exercises_data = []
    for progress in available_progress:
        exercise = build_exercise(
            progress.word,
            progress.pool,
            all_words,
            session_words,
        )
        exercises_data.append(exercise)

    # Sort by exercise type
    sorted_exercises = sort_exercises_by_type(exercises_data)
    exercise_order = get_exercise_order(sorted_exercises)

    # Convert to response format
    exercises = []
    for ex in sorted_exercises:
        exercises.append(ExerciseWithWordSchema(
            word_id=ex["word_id"],
            word=ex["word"],
            translation=ex["translation"],
            image_url=ex["image_url"],
            audio_url=ex["audio_url"],
            pool=ex["pool"],
            type=ex["type"],
            options=[OptionSchema(**opt) for opt in ex["options"]],
            correct_index=ex["correct_index"],
        ))

    return PracticeSessionResponse(
        available=True,
        reason=None,
        exercises=exercises,
        exercise_order=exercise_order,
    )


@router.post("/submit", response_model=PracticeSubmitResponse)
def submit_practice(
    request: PracticeSubmitRequest,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    """Submit practice session answers."""
    progress_repo = ProgressRepository(db)

    now = datetime.now(timezone.utc)
    results = []
    correct_count = 0
    incorrect_count = 0

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

    return PracticeSubmitResponse(
        success=True,
        results=results,
        summary=PracticeSummary(
            correct_count=correct_count,
            incorrect_count=incorrect_count,
        ),
    )
