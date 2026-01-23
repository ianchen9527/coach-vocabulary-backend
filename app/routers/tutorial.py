import random
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.word import Word
from app.repositories.word_repository import WordRepository
from app.schemas.tutorial import (
    VocabularyTutorialResponse,
    TutorialStepSchema,
    TutorialCompleteResponse,
)
from app.schemas.common import OptionSchema, WordDetailSchema
from app.utils.constants import ExerciseType

router = APIRouter(prefix="/api/tutorial", tags=["tutorial"])

# Tutorial words configuration
TARGET_WORD = "apple"
DISTRACTOR_WORDS = ["banana", "grape", "mango"]

# Tutorial exercise types in order
TUTORIAL_EXERCISE_TYPES = [
    ExerciseType.READING_LV1,
    ExerciseType.READING_LV2,
    ExerciseType.LISTENING_LV1,
    ExerciseType.SPEAKING_LV1,
    ExerciseType.SPEAKING_LV2,
]


def build_tutorial_options(
    correct_word: Word,
    distractor_words: List[Word],
) -> tuple[List[OptionSchema], int]:
    """
    Build randomized options for a tutorial step.

    Returns:
        tuple: (options list, correct_index)
    """
    all_words = distractor_words + [correct_word]
    random.shuffle(all_words)

    correct_index = next(
        i for i, w in enumerate(all_words) if w.id == correct_word.id
    )

    options = []
    for i, word in enumerate(all_words):
        options.append(OptionSchema(
            index=i,
            word_id=str(word.id),
            translation=word.translation,
            image_url=word.image_url,
        ))

    return options, correct_index


@router.get("/vocabulary", response_model=VocabularyTutorialResponse)
def get_vocabulary_tutorial(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the vocabulary tutorial session.

    Returns a tutorial with 5 exercise steps using "apple" as the target word
    and "banana", "grape", "mango" as distractors.
    """
    word_repo = WordRepository(db)

    # Fetch target word
    target_word = word_repo.get_by_word(TARGET_WORD)
    if not target_word:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tutorial word '{TARGET_WORD}' not found in database"
        )

    # Fetch distractor words
    distractor_words = []
    for word_name in DISTRACTOR_WORDS:
        word = word_repo.get_by_word(word_name)
        if not word:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tutorial word '{word_name}' not found in database"
            )
        distractor_words.append(word)

    # Build tutorial steps
    steps = []
    target_word_id = str(target_word.id)
    for i, exercise_type in enumerate(TUTORIAL_EXERCISE_TYPES):
        # Speaking exercises don't have options
        if exercise_type in [ExerciseType.SPEAKING_LV1, ExerciseType.SPEAKING_LV2]:
            step = TutorialStepSchema(
                step=i + 1,
                word_id=target_word_id,
                type=exercise_type.value,
                options=[],
                correct_index=None,
            )
        else:
            options, correct_index = build_tutorial_options(target_word, distractor_words)
            step = TutorialStepSchema(
                step=i + 1,
                word_id=target_word_id,
                type=exercise_type.value,
                options=options,
                correct_index=correct_index,
            )
        steps.append(step)

    # Build word detail
    word_detail = WordDetailSchema(
        id=str(target_word.id),
        word=target_word.word,
        translation=target_word.translation,
        sentence=target_word.sentence,
        sentence_zh=target_word.sentence_zh,
        image_url=target_word.image_url,
        audio_url=target_word.audio_url,
    )

    return VocabularyTutorialResponse(
        word=word_detail,
        steps=steps,
    )


@router.post("/vocabulary/complete", response_model=TutorialCompleteResponse)
def complete_vocabulary_tutorial(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark the vocabulary tutorial as completed.

    Sets the vocabulary_tutorial_completed_at timestamp for the current user.
    """
    current_user.vocabulary_tutorial_completed_at = datetime.now(timezone.utc)
    db.commit()

    return TutorialCompleteResponse(success=True)
